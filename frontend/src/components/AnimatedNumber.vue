<template>
  <span class="inline-block tabular-nums">{{ displayValue }}</span>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'

const props = defineProps({
  value: {
    type: Number,
    required: true
  },
  duration: {
    type: Number,
    default: 1500
  },
  suffix: {
    type: String,
    default: ''
  },
  prefix: {
    type: String,
    default: ''
  }
})

const displayValue = ref(props.prefix + '0' + props.suffix)

function animateNumber(start, end, duration) {
  const startTime = performance.now()
  const diff = end - start
  
  function update(currentTime) {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / duration, 1)
    
    const easeOutQuart = 1 - Math.pow(1 - progress, 4)
    const current = Math.floor(start + diff * easeOutQuart)
    
    displayValue.value = props.prefix + current.toLocaleString() + props.suffix
    
    if (progress < 1) {
      requestAnimationFrame(update)
    }
  }
  
  requestAnimationFrame(update)
}

onMounted(() => {
  animateNumber(0, props.value, props.duration)
})

watch(() => props.value, (newVal, oldVal) => {
  animateNumber(oldVal || 0, newVal, props.duration)
})
</script>
