# Kaputt Dataset Structure (README)

We explain the Kaputt dataset structure, how it is implemented, and its

## Dataset Structure

The dataset is organized into query and reference sets, further divided into training (train), validation (validation), and test (test) subsets. Each subset consists of a unique query/reference dataset pair, with non-overlapping item identifiers (item_identifier) to ensure proper model generalization.

### Query Dataset

The query datasets (query-<subset>.parquet) contain image captures with the following associated information:

1. `capture_id`: `str` - Capture ID (unique per sample)
2. `item_identifier`: `str` Item identifier (unique per item)
3. `defect`: `bool` / `major_defect`: `bool` Defect severity (minor, major)
     - Undamaged: `defect = False`
     - Minor damage: `defect = True`
     - Major damage: `defect = True` and `major_defect = True`
4. `defect_types`: `str` Defect type(s) for defective items. Comma separated list, possible values: actuation, deconstruction, deformation, missing_unit, penetration, spillage, superficial
5. `item_material`: `str` Item material. Possible values: cardboard, plastic_loose_bag, plastic_hard, plastic_tight_wrap, plastic_bubble_wrap, book_paper, book_other, book_plastic_tight_wrap, paper, other
6. `query_image`: `str` Relative path to full (non-cropped) image of item in tray of size 2048x2048 in JPEG format 
7. `query_crop`: `str` - Relative path to cropped image of the item of square but otherwise variable size (depending on item dimensions/segmentation mask).
8. `query_mask`: `str` - Relative path to the item segmentation mask with to the uncropped image 

Note that all filenames (image, crop, mask) are named as `<capture_id>.<ext>` where `<ext>` is `jpg` for the images and crops, and `png` for the masks.

### Reference Dataset

The reference dataset (reference-<subset>.parquet) contains 1-3 image captures per item identifier, primarily non-defective. Each includes:

1. `item_identifier`: `str` Item identifier (unique per item)
2. `reference_image`: `str` - Relative paths (comma separated) to full (non-cropped) image of item in tray
3. `reference_crop`: `str` - Relative paths (comma separated) to cropped image of the item 
4. `reference_mask`: `str` - Relative paths (comma separated) to the item segmentation mask

Use the item_identifier to join the reference with the query samples. 
Attention: there up to 3 reference captures for each item identifier!

## File Structure

The dataset is organized as follows:

```plaintext
<root_path>/
├── query-train.parquet
├── query-validation.parquet
├── query-test.parquet
├── reference-train.parquet
├── reference-validation.parquet
├── reference-test.parquet
└── kaputt-release/
    ├── train/
    │   ├── query-data/
    │   │   ├── image/
    │   │   ├── crop/
    │   │   └── mask/
    │   └── reference-data/
    │       ├── image/
    │       ├── crop/
    │       └── mask/
    ├── validation/
    │   ├── query-data/
    │   │   ├── image/
    │   │   ├── crop/
    │   │   └── mask/
    │   └── reference-data/
    │       ├── image/
    │       ├── crop/
    │       └── mask/
    └── test/
        ├── query-data/
        │   ├── image/
        │   ├── crop/
        │   └── mask/
        └── reference-data/
            ├── image/
            ├── crop/
            └── mask/
```


## PyTorch Dataloader Example

Here's an example of how to create a PyTorch dataloader for this dataset:

```python
import argparse
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
from pathlib import Path


def pad_tensor(tensor, target_size, pad_value=0):
    pad_size = target_size - tensor.size(0)
    if pad_size <= 0:
        return tensor[:target_size]
    return torch.cat([tensor, torch.full((pad_size, *tensor.size()[1:]), pad_value)])


class KaputtDataset(Dataset):
    def __init__(self, root_path, subset='train', transform=None, image_size=(224, 224), max_references=3):
        self.root_path = Path(root_path)
        self.subset = subset
        self.image_size = image_size
        self.max_references = max_references

        # Define default transform if none provided
        if transform is None:
            self.transform = transforms.Compose([
                transforms.Resize(image_size),
                transforms.ToTensor(),
            ])
        else:
            self.transform = transform

        # Load query data
        self.query_data = pd.read_parquet(self.root_path / f'query-{subset}.parquet')

        # Load reference data
        self.reference_data = pd.read_parquet(self.root_path / f'reference-{subset}.parquet')

    def __len__(self):
        return len(self.query_data)

    def __getitem__(self, idx):
        query_row = self.query_data.iloc[idx]

        # Load query images and mask
        query_image = Image.open(self.root_path / query_row.query_image)
        query_crop = Image.open(self.root_path / query_row.query_crop)
        query_mask = Image.open(self.root_path / query_row.query_mask)

        # Load reference images and masks from exploded dataframe
        reference_rows = self.reference_data[self.reference_data.item_identifier == query_row.item_identifier]
        reference_image = [Image.open(self.root_path / row.reference_image) for _, row in reference_rows.iterrows()]
        reference_crop = [Image.open(self.root_path / row.reference_crop) for _, row in reference_rows.iterrows()]
        reference_mask = [Image.open(self.root_path / row.reference_mask) for _, row in reference_rows.iterrows()]

        # Apply transforms to all images
        query_image = self.transform(query_image)
        query_crop = self.transform(query_crop)
        query_mask = self.transform(query_mask)
        reference_image = torch.stack([self.transform(img) for img in reference_image])
        reference_crop = torch.stack([self.transform(crop) for crop in reference_crop])
        reference_mask = torch.stack([self.transform(mask) for mask in reference_mask])

        # Pad reference tensors
        reference_image = pad_tensor(reference_image, self.max_references)
        reference_crop = pad_tensor(reference_crop, self.max_references)
        reference_mask = pad_tensor(reference_mask, self.max_references)

        return {
            'query_image': query_image,
            'query_crop': query_crop,
            'query_mask': query_mask,
            'reference_image': reference_image,
            'reference_crop': reference_crop,
            'reference_mask': reference_mask,
            'item_material': query_row.item_material,
            'defect': torch.tensor(bool(query_row.defect), dtype=torch.bool),
            'major_defect': torch.tensor(bool(query_row.major_defect), dtype=torch.bool),
            'defect_types': query_row.defect_types,
            'capture_id': query_row.capture_id,
            'item_identifier': query_row.item_identifier
        }


def load_kaputt_dataset(batch_size=32, num_workers=4) -> DataLoader:
    parser = argparse.ArgumentParser(description="Data Sanity Check")
    parser.add_argument("--root-path", type=str, default=".",
                        help="Root path for the dataset")
    parser.add_argument("--subset", type=str, default='train',
                        help="Subset to load (default: train)")
    parser.add_argument("--image-size", type=int, nargs=2, default=[224, 224],
                        help="Image size (height, width) to resize to")
    parser.add_argument("--max-references", type=int, default=3,
                        help="Maximum number of reference images to use")
    args = parser.parse_args()

    dataset = KaputtDataset(args.root_path, subset=args.subset, image_size=tuple(args.image_size),
                            max_references=args.max_references)
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers
    )

    # Test the dataloader
    for batch in dataloader:
        print("Batch sizes:")
        print("Query image:", batch['query_image'].shape)
        print("Query crop:", batch['query_crop'].shape)
        print("Query mask:", batch['query_mask'].shape)
        print("Reference image:", batch['reference_image'].shape)
        print("Reference crop:", batch['reference_crop'].shape)
        print("Reference mask:", batch['reference_mask'].shape)
        print("Defect labels:", batch['defect'])
        print("Item materials:", batch['item_material'])
        print("Defect types:", batch['defect_types'])
        break

    return dataset


if __name__ == "__main__":
    kaputt_dataset = load_kaputt_dataset()
```

Expected output (exact values may differ due to randomness):

```plaintext
Batch sizes:
Query image: torch.Size([32, 3, 224, 224])
Query crop: torch.Size([32, 3, 224, 224])
Query mask: torch.Size([32, 1, 224, 224])
Reference images: torch.Size([32, 3, 3, 224, 224])
Reference crops: torch.Size([32, 3, 3, 224, 224])
Reference masks: torch.Size([32, 3, 1, 224, 224])
Defect labels: torch.Size([32])
Item materials: ['plastic_bubble_wrap', 'cardboard', 'cardboard', 'other', 'cardboard', 'plastic_hard', 'cardboard', 'book_paper', 'plastic_loose_bag', 'plastic_tight_wrap', 'book_paper', 'cardboard', 'paper', 'plastic_loose_bag', 'cardboard', 'cardboard', 'cardboard', 'cardboard', 'book_paper', 'book_paper', 'book_paper', 'plastic_loose_bag', 'plastic_loose_bag', 'cardboard', 'plastic_tight_wrap', 'cardboard', 'cardboard', 'plastic_loose_bag', 'plastic_loose_bag', 'cardboard', 'plastic_bubble_wrap', 'plastic_hard']
Defect types: ['', 'deformation,penetration', 'actuation,penetration', '', 'deformation,penetration', 'deconstruction,deformation', 'deformation,superficial', '', '', 'actuation,deconstruction,penetration', '', '', 'penetration', '', '', '', 'actuation,deformation', 'actuation,superficial', 'deformation', 'actuation,deconstruction,deformation', '', '', '', '', '', '', '', '', '', '', '', '']
```


This example creates a custom `KaputtDataset` class that loads both query and reference data from the parquet files and the corresponding images. The `__getitem__` method returns a dictionary containing the query images, crops, and masks, as well as the reference images and masks, along with the labels.

The dataloader can be easily customized to suit your specific needs, such as adding data augmentation, handling different subsets, or incorporating additional preprocessing steps.
