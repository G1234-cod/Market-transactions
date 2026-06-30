<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold gradient-text">管理员控制台</h1>
        <p class="text-text-muted text-sm mt-1">管理平台数据、测试模型效果、审核商品</p>
      </div>
      <div class="badge badge-warning">管理员</div>
    </div>

    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
      <div class="stat-card cursor-pointer hover:shadow-lg hover:-translate-y-0.5 transition-all" @click="activeTab = 'users'">
        <div class="stat-value text-primary-600">{{ stats.overview?.users || 0 }}</div>
        <div class="stat-label">👤 注册用户</div>
      </div>
      <div class="stat-card cursor-pointer hover:shadow-lg hover:-translate-y-0.5 transition-all" @click="activeTab = 'review'">
        <div class="stat-value text-accent-600">{{ stats.overview?.published_items || 0 }}</div>
        <div class="stat-label">📦 已发布商品</div>
      </div>
      <div class="stat-card cursor-pointer hover:shadow-lg hover:-translate-y-0.5 transition-all" @click="activeTab = 'cases'">
        <div class="stat-value text-warning-600">{{ stats.model_performance?.hard_cases?.unfixed || 0 }}</div>
        <div class="stat-label">🔧 待修复错误案例</div>
      </div>
    </div>

    <div class="flex flex-wrap gap-2 mb-6">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="pill-button"
        :class="activeTab === tab.id ? 'pill-button-active' : 'pill-button-inactive'"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <transition name="page" mode="out-in">
      <div :key="activeTab">
      <!-- ==================== 数据概览 ==================== -->
      <div v-if="activeTab === 'stats'" class="space-y-6">
        <div class="glass-card">
          <div class="bg-gradient-to-r from-primary-50 to-accent-50 px-6 py-4 border-b border-border">
            <div class="flex items-center justify-between">
              <h2 class="font-semibold text-text-primary">📊 系统数据概览</h2>
              <button @click="doSyncQdrant" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-accent-100 text-accent-700 border border-accent-200 hover:bg-accent-200 transition-all">
                🔄 同步向量库
              </button>
            </div>
          </div>
          <div class="p-6">
            <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
              <div class="bg-surface-secondary rounded-xl p-4">
                <div class="text-2xl font-bold text-text-primary">{{ stats.overview?.total_items || 0 }}</div>
                <div class="text-xs text-text-muted">商品总数</div>
              </div>
              <div class="bg-surface-secondary rounded-xl p-4">
                <div class="text-2xl font-bold text-text-primary">{{ stats.overview?.categories || 0 }}</div>
                <div class="text-xs text-text-muted">品类数</div>
              </div>
              <div class="bg-surface-secondary rounded-xl p-4">
                <div class="text-2xl font-bold text-text-primary">{{ stats.overview?.brands || 0 }}</div>
                <div class="text-xs text-text-muted">品牌数</div>
              </div>
              <div class="bg-surface-secondary rounded-xl p-4">
                <div class="text-2xl font-bold text-text-primary">{{ stats.overview?.audit_logs || 0 }}</div>
                <div class="text-xs text-text-muted">审计日志</div>
              </div>
              <div class="bg-surface-secondary rounded-xl p-4">
                <div class="text-2xl font-bold text-text-primary">{{ stats.overview?.notifications || 0 }}</div>
                <div class="text-xs text-text-muted">通知数</div>
              </div>
            </div>

            <div class="grid md:grid-cols-2 gap-6">
              <div>
                <h3 class="text-sm font-semibold text-text-secondary mb-3">模型错误案例统计</h3>
                <div class="space-y-3">
                  <div class="flex items-center justify-between">
                    <span class="text-sm text-text-muted">总错误案例</span>
                    <span class="font-semibold">{{ stats.model_performance?.hard_cases?.total || 0 }}</span>
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-sm text-text-muted">已修复</span>
                    <span class="font-semibold text-accent-600">{{ stats.model_performance?.hard_cases?.fixed || 0 }}</span>
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-sm text-text-muted">待修复</span>
                    <span class="font-semibold text-warning-600">{{ stats.model_performance?.hard_cases?.unfixed || 0 }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ==================== 模型测试 ==================== -->
      <div v-else-if="activeTab === 'test'" key="test" class="space-y-6">
        <div class="glass-card">
          <div class="bg-gradient-to-r from-primary-50 to-accent-50 px-6 py-4 border-b border-border">
            <h2 class="font-semibold text-text-primary">🧪 模型测试</h2>
          </div>
          <div class="p-6">
            <div
              class="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-primary-300 transition-colors cursor-pointer"
              @click="$refs.fileInput.click()" @dragover.prevent @drop.prevent="handleDrop"
            >
              <div v-if="!testImage" class="space-y-3">
                <div class="text-4xl">📷</div>
                <p class="text-text-muted">点击或拖拽上传图片进行模型测试</p>
                <p class="text-xs text-text-light">支持 JPG、PNG 格式 · 可连续上传测试多张</p>
              </div>
              <div v-else class="flex flex-col items-center">
                <img :src="testImage" class="max-h-48 rounded-lg object-contain" />
                <p class="text-sm text-text-secondary mt-2">{{ testImageName }}</p>
              </div>
              <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="handleFileSelect" />
            </div>

            <!-- 批量测试 -->
            <div class="flex items-center gap-3 mt-4">
              <button
                class="btn-primary flex-1"
                :disabled="!testImage || testing"
                @click="doTestModel"
              >
                <span v-if="testing" class="loading-spinner mr-2" />
                <span>{{ testing ? '模型测试中...' : '🚀 开始单张测试' }}</span>
              </button>
              <button
                class="btn-outline"
                :disabled="!testImage || testing"
                @click="doBatchTest"
              >
                批量测试 ({{ batchCount }}张)
              </button>
            </div>

            <!-- 批量测试结果统计 -->
            <div v-if="batchResults.length > 0" class="mt-4 glass-card p-4 bg-accent-50">
              <h3 class="text-sm font-semibold text-accent-700 mb-3">📊 批量测试结果</h3>
              <div class="grid grid-cols-4 gap-3 text-center">
                <div>
                  <div class="text-xl font-bold text-text-primary">{{ batchResults.length }}</div>
                  <div class="text-xs text-text-muted">总测试数</div>
                </div>
                <div>
                  <div class="text-xl font-bold text-accent-600">{{ batchAgreeCount }}</div>
                  <div class="text-xs text-text-muted">模型一致</div>
                </div>
                <div>
                  <div class="text-xl font-bold text-warning-600">{{ batchDisagreeCount }}</div>
                  <div class="text-xs text-text-muted">模型不一致</div>
                </div>
                <div>
                  <div class="text-xl font-bold text-text-primary">{{ batchAgreementRate }}%</div>
                  <div class="text-xs text-text-muted">一致率</div>
                </div>
              </div>
              <button class="btn-secondary-sm mt-3" @click="batchResults = []">清除结果</button>
            </div>

            <!-- 单张测试结果 -->
            <div v-if="testResult" class="mt-6 space-y-4">
              <div class="glass-card">
                <div class="px-4 py-3 border-b border-border">
                  <h3 class="font-semibold text-sm">测试结果</h3>
                </div>
                <div class="p-4">
                  <div class="grid md:grid-cols-2 gap-4">
                    <div>
                      <h4 class="text-xs font-medium text-text-muted mb-2">最终识别结果</h4>
                      <div class="space-y-2">
                        <div class="flex items-center gap-2">
                          <span class="text-xs text-text-muted w-16">品类</span>
                          <span class="font-medium">{{ testResult.final_result?.category || '-' }}</span>
                        </div>
                        <div class="flex items-center gap-2">
                          <span class="text-xs text-text-muted w-16">品牌</span>
                          <span class="font-medium">{{ testResult.final_result?.brand || '-' }}</span>
                        </div>
                        <div class="flex items-center gap-2">
                          <span class="text-xs text-text-muted w-16">型号</span>
                          <span class="font-medium">{{ testResult.final_result?.model || '-' }}</span>
                        </div>
                        <div class="flex items-center gap-2">
                          <span class="text-xs text-text-muted w-16">市场均价</span>
                          <span class="font-medium">¥{{ testResult.final_result?.market_avg_price || 0 }}</span>
                        </div>
                      </div>
                    </div>
                    <div>
                      <h4 class="text-xs font-medium text-text-muted mb-2">模型对比</h4>
                      <div class="space-y-2">
                        <div class="flex items-center justify-between">
                          <span class="text-xs">YOLO识别</span>
                          <span :class="testResult.model_comparison?.yolo?.success ? 'text-accent-600' : 'text-danger-600'">
                            {{ testResult.model_comparison?.yolo?.success ? '✓ 成功' : '✗ 失败' }}
                          </span>
                        </div>
                        <div class="flex items-center justify-between">
                          <span class="text-xs">Qwen识别</span>
                          <span :class="testResult.model_comparison?.qwen?.success ? 'text-accent-600' : 'text-danger-600'">
                            {{ testResult.model_comparison?.qwen?.success ? '✓ 成功' : '✗ 失败' }}
                          </span>
                        </div>
                        <div class="flex items-center justify-between">
                          <span class="text-xs">瑕疵检测</span>
                          <span :class="testResult.defect_result?.success ? 'text-accent-600' : 'text-danger-600'">
                            {{ testResult.defect_result?.success ? '✓ 成功 (' + (testResult.defect_result?.defect_count || 0) + '处)' : '✗ 失败' }}
                          </span>
                        </div>
                        <div class="flex items-center justify-between">
                          <span class="text-xs">模型一致性</span>
                          <span :class="testResult.model_comparison?.has_disagreement ? 'text-warning-600' : 'text-accent-600'">
                            {{ testResult.model_comparison?.has_disagreement ? '⚠ 不一致' : '✓ 一致' }}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 模型不一致提示 -->
              <div v-if="testResult.model_comparison?.has_disagreement" class="glass-card bg-warning-50">
                <div class="px-4 py-3 border-b border-warning-200">
                  <h3 class="font-semibold text-sm text-warning-700">⚠️ 模型结果不一致</h3>
                </div>
                <div class="p-4">
                  <div class="grid grid-cols-2 gap-4">
                    <div class="bg-white rounded-lg p-3">
                      <div class="text-xs text-text-muted mb-1">自研YOLO模型</div>
                      <div class="font-semibold">{{ testResult.model_comparison?.yolo?.category || '-' }}</div>
                      <div class="text-xs text-text-muted">置信度: {{ (testResult.model_comparison?.yolo?.confidence * 100)?.toFixed(1) || 0 }}%</div>
                    </div>
                    <div class="bg-white rounded-lg p-3">
                      <div class="text-xs text-text-muted mb-1">阿里云Qwen模型</div>
                      <div class="font-semibold">{{ testResult.model_comparison?.qwen?.category || '-' }}</div>
                      <div class="text-xs text-text-muted">品牌: {{ testResult.model_comparison?.qwen?.brand || '-' }}</div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 瑕疵检测结果（含标注图） -->
              <div v-if="testResult.defect_result?.defect_count > 0" class="glass-card">
                <div class="px-4 py-3 border-b border-border bg-gradient-to-r from-danger-50 to-warning-50">
                  <h3 class="font-semibold text-sm text-danger-700">🔍 瑕疵检测结果</h3>
                </div>
                <div class="p-4">
                  <div class="flex flex-col md:flex-row gap-4">
                    <!-- 标注图 -->
                    <div v-if="testResult.defect_result?.annotated_url" class="flex-shrink-0">
                      <p class="text-xs text-text-muted mb-2">瑕疵标注图：</p>
                      <img
                        :src="testResult.defect_result.annotated_url"
                        class="max-h-72 rounded-lg object-contain border border-border shadow-sm"
                        alt="瑕疵标注图"
                      />
                    </div>
                    <div class="flex-1">
                      <div class="flex items-center gap-3 mb-3">
                        <div class="text-3xl font-bold text-danger-600">{{ testResult.defect_result.defect_count }}</div>
                        <div>
                          <div class="text-sm text-text-muted">处瑕疵</div>
                          <div class="text-xs text-text-light">详见下方标签</div>
                        </div>
                      </div>
                      <div class="flex flex-wrap gap-2">
                        <span v-for="(defect, index) in testResult.defect_result?.defects" :key="index"
                          class="badge"
                          :class="getDefectBadgeClass(defect.severity)">
                          {{ defect.type_cn }}
                          <span class="text-xs ml-1 opacity-75">
                            ({{ (defect.confidence * 100).toFixed(0) }}%
                            <template v-if="defect.severity_label"> · {{ defect.severity_label }}</template>)
                          </span>
                        </span>
                      </div>
                      <!-- 瑕疵统计 -->
                      <div v-if="defectTypeSummary.length > 0" class="mt-4 grid grid-cols-2 gap-2">
                        <div v-for="dt in defectTypeSummary" :key="dt.type" class="flex items-center justify-between text-xs">
                          <span class="text-text-muted">{{ dt.type_cn }}</span>
                          <span class="font-semibold">{{ dt.count }}处</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 原图对比 -->
              <div v-if="testResult.image_urls?.length" class="mt-2">
                <p class="text-xs text-text-muted mb-2">原图：</p>
                <img :src="testResult.image_urls[0]" class="max-h-48 rounded-lg object-contain border border-border" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ==================== 商品审核 ==================== -->
      <div v-else-if="activeTab === 'review'" key="review" class="space-y-6">
        <div class="glass-card">
          <div class="bg-gradient-to-r from-primary-50 to-accent-50 px-6 py-4 border-b border-border flex items-center justify-between flex-wrap gap-3">
            <h2 class="font-semibold text-text-primary">🔍 商品审核</h2>
            <div class="flex items-center gap-2">
              <input
                v-model="reviewSearch"
                placeholder="搜索商品..."
                class="input-field-sm w-40"
                autocomplete="off"
              />
              <select v-model="reviewStatusFilter" class="input-field-sm w-32" @change="loadReviewItems">
                <option value="">全部状态</option>
                <option value="normal">正常</option>
                <option value="flagged">待审核</option>
                <option value="forced_delisted">已强制下架</option>
              </select>
            </div>
          </div>
          <div class="p-6">
            <div v-if="filteredReviewItems.length === 0" class="text-center py-8 text-text-muted">
              <div class="text-4xl mb-2">📭</div>
              <p>{{ reviewItems.length === 0 ? '暂无商品数据' : '没有匹配的商品' }}</p>
            </div>
            <div v-else class="space-y-4">
              <div v-for="item in filteredReviewItems" :key="item.id" class="glass-card p-4">
                <div class="flex gap-4">
                  <img
                    :src="item.original_image_url"
                    class="w-24 h-24 rounded-lg object-cover flex-shrink-0"
                    @error="e => e.target.style.display = 'none'"
                  />
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center justify-between">
                      <h3 class="font-semibold text-text-primary truncate">{{ item.ai_generated_title }}</h3>
                      <span :class="getStatusClass(item.review_status)" class="badge">{{ getStatusText(item.review_status) }}</span>
                    </div>
                    <div class="flex items-center gap-4 mt-1 text-xs text-text-muted flex-wrap">
                      <span>👤 {{ item.username }}</span>
                      <span>{{ item.category }} / {{ item.brand }} / {{ item.model }}</span>
                      <span class="text-accent-600 font-semibold">¥{{ item.suggested_price }}</span>
                    </div>
                    <div class="flex items-center gap-2 mt-3">
                      <button
                        v-if="item.status === 'published' && item.review_status !== 'forced_delisted'"
                        class="btn-danger-sm"
                        @click="confirmForceDelist(item)"
                      >
                        强制下架
                      </button>
                      <span class="text-xs text-text-muted">{{ formatDate(item.created_at) }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ==================== 训练指标 ==================== -->
      <div v-else-if="activeTab === 'metrics'" key="metrics" class="space-y-6">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- 模型卡片模板 -->
          <template v-for="m in [
            { key: 'yolo', title: '分类模型', subtitle: 'YOLOv8n 商品分类识别', icon: '🔍', color: 'blue', data: yoloMetrics },
            { key: 'defect', title: '瑕疵检测模型', subtitle: 'YOLOv8n 缺陷检测与成色分级', icon: '🔬', color: 'amber', data: defectMetrics }
          ]" :key="m.key">
            <div class="glass-card overflow-hidden">
              <div :class="`bg-gradient-to-r ${m.color === 'blue' ? 'from-blue-500 to-blue-600' : 'from-amber-500 to-orange-600'} px-6 py-4`">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center text-white text-lg font-bold">{{ m.icon }}</div>
                    <div>
                      <h3 class="font-bold text-white text-lg">{{ m.title }}</h3>
                      <p class="text-xs opacity-80">{{ m.subtitle }}</p>
                    </div>
                  </div>
                  <div v-if="m.data.train_date" class="text-right text-xs text-white/70">
                    <div>训练日期</div>
                    <div class="font-medium">{{ m.data.train_date?.slice(0, 10) }}</div>
                  </div>
                </div>
              </div>
              <div class="p-5 space-y-4">
                <template v-if="m.data.train_metrics">
                  <!-- 核心指标 -->
                  <div class="grid grid-cols-2 gap-2">
                    <div :class="`${m.color === 'blue' ? 'bg-blue-50' : 'bg-amber-50'} rounded-xl p-3 text-center`">
                      <div :class="`text-xl font-extrabold ${m.color === 'blue' ? 'text-blue-700' : 'text-amber-700'}`">{{ fmtPct(m.data.train_metrics.precision) }}</div>
                      <div :class="`text-xs ${m.color === 'blue' ? 'text-blue-500' : 'text-amber-500'} mt-0.5`">精确率 Precision</div>
                    </div>
                    <div :class="`${m.color === 'blue' ? 'bg-blue-50' : 'bg-amber-50'} rounded-xl p-3 text-center`">
                      <div :class="`text-xl font-extrabold ${m.color === 'blue' ? 'text-blue-700' : 'text-amber-700'}`">{{ fmtPct(m.data.train_metrics.recall) }}</div>
                      <div :class="`text-xs ${m.color === 'blue' ? 'text-blue-500' : 'text-amber-500'} mt-0.5`">召回率 Recall</div>
                    </div>
                    <div :class="`${m.color === 'blue' ? 'bg-blue-50' : 'bg-amber-50'} rounded-xl p-3 text-center`">
                      <div :class="`text-xl font-extrabold ${m.color === 'blue' ? 'text-blue-700' : 'text-amber-700'}`">{{ fmtPct(m.data.train_metrics.map50) }}</div>
                      <div :class="`text-xs ${m.color === 'blue' ? 'text-blue-500' : 'text-amber-500'} mt-0.5`">mAP@50</div>
                    </div>
                    <div :class="`${m.color === 'blue' ? 'bg-blue-50' : 'bg-amber-50'} rounded-xl p-3 text-center`">
                      <div :class="`text-xl font-extrabold ${m.color === 'blue' ? 'text-blue-700' : 'text-amber-700'}`">{{ fmtPct(m.data.train_metrics.map50_95) }}</div>
                      <div :class="`text-xs ${m.color === 'blue' ? 'text-blue-500' : 'text-amber-500'} mt-0.5`">mAP@50-95</div>
                    </div>
                  </div>

                  <!-- Loss 曲线 -->
                  <div class="border-t border-border pt-3">
                    <div class="text-xs text-text-muted font-medium mb-2">验证 Loss</div>
                    <div class="grid grid-cols-3 gap-2">
                      <div class="bg-surface-secondary rounded-lg p-2 text-center">
                        <div class="text-sm font-semibold text-text-primary">{{ m.data.train_metrics.box_loss?.toFixed(3) }}</div>
                        <div class="text-xs text-text-muted">Box</div>
                      </div>
                      <div class="bg-surface-secondary rounded-lg p-2 text-center">
                        <div class="text-sm font-semibold text-text-primary">{{ m.data.train_metrics.cls_loss?.toFixed(3) }}</div>
                        <div class="text-xs text-text-muted">Cls</div>
                      </div>
                      <div class="bg-surface-secondary rounded-lg p-2 text-center">
                        <div class="text-sm font-semibold text-text-primary">{{ m.data.train_metrics.dfl_loss?.toFixed(3) }}</div>
                        <div class="text-xs text-text-muted">DFL</div>
                      </div>
                    </div>
                  </div>

                  <!-- 模型参数 -->
                  <div class="border-t border-border pt-3">
                    <div class="text-xs text-text-muted font-medium mb-2">核心训练参数</div>
                    <div class="grid grid-cols-3 gap-x-3 gap-y-1.5 text-xs">
                      <div class="flex justify-between"><span class="text-text-muted">基础模型</span><span class="font-medium">{{ m.data.train_params?.base_model || '-' }}</span></div>
                      <div class="flex justify-between"><span class="text-text-muted">训练轮数</span><span class="font-medium">{{ m.data.train_params?.epochs }}</span></div>
                      <div class="flex justify-between"><span class="text-text-muted">Batch</span><span class="font-medium">{{ m.data.train_params?.batch_size }}</span></div>
                      <div class="flex justify-between"><span class="text-text-muted">图片尺寸</span><span class="font-medium">{{ m.data.train_params?.image_size }}px</span></div>
                      <div class="flex justify-between"><span class="text-text-muted">学习率</span><span class="font-medium">{{ m.data.train_params?.learning_rate }}</span></div>
                      <div class="flex justify-between"><span class="text-text-muted">优化器</span><span class="font-medium">{{ m.data.train_params?.optimizer }}</span></div>
                      <div class="flex justify-between"><span class="text-text-muted">设备</span><span class="font-medium">{{ m.data.train_params?.device }}</span></div>
                      <div class="flex justify-between"><span class="text-text-muted">Dropout</span><span class="font-medium">{{ m.data.train_params?.dropout }}</span></div>
                      <div class="flex justify-between"><span class="text-text-muted">Cos LR</span><span class="font-medium">{{ m.data.train_params?.cos_lr ? '✓' : '✗' }}</span></div>
                      <div class="flex justify-between"><span class="text-text-muted">类别数</span><span class="font-medium">{{ m.data.model_arch?.num_classes }}</span></div>
                      <div class="flex justify-between"><span class="text-text-muted">模型大小</span><span class="font-medium">{{ m.data.file_size_kb ? (m.data.file_size_kb / 1024).toFixed(1) + ' MB' : '-' }}</span></div>
                      <div class="flex justify-between"><span class="text-text-muted">训练耗时</span><span class="font-medium">{{ fmtTime(m.data.training_time_seconds) }}</span></div>
                    </div>
                  </div>
                </template>
                <div v-else class="text-center py-8 text-text-muted">
                  <div class="text-4xl mb-2">📊</div>
                  <p class="text-sm">{{ m.data.error || '暂无训练数据' }}</p>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- ==================== 错误案例 ==================== -->
      <div v-else-if="activeTab === 'cases'" key="cases" class="space-y-6">
        <div class="glass-card">
          <div class="bg-gradient-to-r from-primary-50 to-accent-50 px-6 py-4 border-b border-border flex items-center justify-between">
            <h2 class="font-semibold text-text-primary">📝 错误案例管理</h2>
            <select v-model="casesFilter" class="input-field-sm w-32" @change="loadHardCases">
              <option :value="false">待修复</option>
              <option :value="true">已修复</option>
            </select>
          </div>
          <div class="p-6">
            <div v-if="hardCases.length === 0" class="text-center py-8 text-text-muted">
              <div class="text-4xl mb-2">📋</div>
              <p>暂无错误案例</p>
            </div>
            <div v-else class="space-y-4">
              <div v-for="itemCase in hardCases" :key="itemCase.id" class="glass-card p-4">
                <div class="flex gap-4">
                  <img :src="itemCase.image_url" class="w-20 h-20 rounded-lg object-cover" />
                  <div class="flex-1">
                    <div class="flex items-center gap-2">
                      <span class="badge badge-danger">错误: {{ itemCase.wrong_label }}</span>
                      <span class="badge badge-success">正确: {{ itemCase.correct_label }}</span>
                    </div>
                    <div class="flex items-center gap-4 mt-2 text-xs text-text-muted">
                      <span>置信度: {{ itemCase.confidence ? (itemCase.confidence * 100).toFixed(2) + '%' : '-' }}</span>
                      <span>重试: {{ itemCase.retry_count }}次</span>
                      <span>{{ formatDate(itemCase.created_at) }}</span>
                    </div>
                  </div>
                  <div class="flex items-center">
                    <button
                      v-if="!itemCase.is_fixed"
                      class="btn-success-sm"
                      @click="markCaseFixed(itemCase.id)"
                    >
                      标记已修复
                    </button>
                    <span v-else class="badge badge-success">已修复</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <!-- ==================== 用户管理 ==================== -->
      <div v-if="activeTab === 'users'" key="users" class="space-y-6">
        <div class="glass-card">
          <div class="bg-gradient-to-r from-primary-50 to-accent-50 px-6 py-4 border-b border-border flex items-center justify-between">
            <h2 class="font-semibold text-text-primary">👤 用户管理</h2>
            <span class="text-xs text-text-muted">{{ adminUsers.length }} 个用户</span>
          </div>
          <div class="p-6">
            <!-- 新增用户 -->
            <div class="flex gap-3 mb-6">
              <input v-model="newUsername" placeholder="用户名" class="input-field flex-1" />
              <input v-model="newPassword" placeholder="密码" class="input-field flex-1" type="password" />
              <select v-model="newUserRole" class="input-field w-28">
                <option value="user">普通用户</option>
                <option value="admin">管理员</option>
              </select>
              <button class="btn-primary-sm whitespace-nowrap" @click="addUser" :disabled="!newUsername || !newPassword">➕ 添加</button>
            </div>
            <!-- 用户列表 -->
            <div class="space-y-2">
              <div v-for="u in adminUsers" :key="u.id" class="flex items-center justify-between px-4 py-3 border border-border rounded-xl hover:bg-surface-secondary transition-colors">
                <div class="flex items-center gap-4">
                  <span class="font-medium text-text-primary">{{ u.username }}</span>
                  <span class="text-xs px-2 py-0.5 rounded-full" :class="u.role === 'admin' ? 'bg-warning-100 text-warning-700' : 'bg-primary-100 text-primary-700'">{{ u.role }}</span>
                  <span class="text-xs px-2 py-0.5 rounded-full" :class="u.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'">{{ u.status === 'active' ? '正常' : '已禁用' }}</span>
                  <span class="text-xs text-text-muted">{{ u.created_at?.slice(0,10) }}</span>
                </div>
                <div class="flex items-center gap-2">
                  <button @click="toggleUser(u)" class="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
                    :class="u.status === 'active' ? 'bg-red-50 text-red-600 border border-red-200 hover:bg-red-100' : 'bg-green-50 text-green-600 border border-green-200 hover:bg-green-100'">
                    {{ u.status === 'active' ? '🔒 禁用' : '🔓 启用' }}
                  </button>
                  <button @click="deleteUser(u)" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-red-50 text-red-600 border border-red-200 hover:bg-red-100">🗑 删除</button>
                </div>
              </div>
              <div v-if="!adminUsers.length" class="text-center py-8 text-text-muted">暂无用户</div>
            </div>
          </div>
        </div>
      </div>

      </div> <!-- end :key wrapper -->
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  getAdminSystemStats,
  testModel,
  getAdminReviewItems,
  forceDelistItem,
  getCheckpointMetrics,
  getAdminUsers,
  createAdminUser,
  deleteAdminUser,
  toggleUserStatus,
  getAdminHardCases,
  markHardCaseFixed,
  syncQdrant,
} from '../api/index.js'

const router = useRouter()

const tabs = [
  { id: 'stats', label: '📊 数据概览' },
  { id: 'test', label: '🧪 模型测试' },
  { id: 'review', label: '🔍 商品审核' },
  { id: 'metrics', label: '📈 训练指标' },
  { id: 'cases', label: '📝 错误案例' },
  { id: 'users', label: '👤 用户管理' },
]

const activeTab = ref('stats')

// ==================== Stats ====================
const stats = ref({})

// ==================== Test ====================
const testImage = ref(null)
const testImageName = ref('')
const testing = ref(false)
const testResult = ref(null)
const batchResults = ref([])
const batchCount = ref(1)
const fileInput = ref(null)  // ✅ 修复：Vue ref 替代 document.querySelector

// ==================== Review ====================
const reviewItems = ref([])
const reviewStatusFilter = ref('')
const reviewSearch = ref('')

// ==================== Metrics ====================
const yoloMetrics = ref({})
const defectMetrics = ref({})

function fmtPct(val) {
  if (val == null || isNaN(val)) return '-'
  return (val * 100).toFixed(2) + '%'
}
function fmtTime(seconds) {
  if (!seconds || seconds <= 0) return '-'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

// ==================== Users ====================
const adminUsers = ref([])
const newUsername = ref('')
const newPassword = ref('')
const newUserRole = ref('user')

// ==================== Cases ====================
const hardCases = ref([])
const casesFilter = ref(false)

// ==================== Computed ====================

const filteredReviewItems = computed(() => {
  if (!reviewSearch.value) return reviewItems.value
  const q = reviewSearch.value.toLowerCase()
  return reviewItems.value.filter(item =>
    (item.ai_generated_title || '').toLowerCase().includes(q) ||
    (item.username || '').toLowerCase().includes(q) ||
    (item.brand || '').toLowerCase().includes(q) ||
    (item.model || '').toLowerCase().includes(q)
  )
})

const batchAgreeCount = computed(() =>
  batchResults.value.filter(r => !r.model_comparison?.has_disagreement).length
)
const batchDisagreeCount = computed(() =>
  batchResults.value.filter(r => r.model_comparison?.has_disagreement).length
)
const batchAgreementRate = computed(() => {
  if (batchResults.value.length === 0) return 0
  return Math.round((batchAgreeCount.value / batchResults.value.length) * 100)
})

// 瑕疵类型统计
const defectTypeSummary = computed(() => {
  if (!testResult.value?.defect_result?.defects) return []
  const map = {}
  for (const d of testResult.value.defect_result.defects) {
    const key = d.type_cn || d.type || '未知'
    if (!map[key]) map[key] = { type_cn: key, count: 0 }
    map[key].count++
  }
  return Object.values(map)
})

// ==================== Methods ====================

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

function getStatusClass(status) {
  switch (status) {
    case 'normal': return 'badge-default'
    case 'flagged': return 'badge-warning'
    case 'forced_delisted': return 'badge-danger'
    default: return 'badge-default'
  }
}

function getStatusText(status) {
  switch (status) {
    case 'normal': return '正常'
    case 'flagged': return '待审核'
    case 'forced_delisted': return '已强制下架'
    default: return status
  }
}

function getDefectBadgeClass(severity) {
  switch (severity) {
    case 'severe': return 'badge-danger'
    case 'moderate': return 'badge-warning'
    case 'minor': return 'badge-default'
    case 'slight': return 'badge-default'
    default: return 'badge-warning'
  }
}

// ==================== Load Data ====================

async function loadStats() {
  try {
    stats.value = await getAdminSystemStats()
  } catch (e) {
    console.error('加载统计失败:', e)
    if (e.response?.status === 403) {
      router.push('/')
    }
  }
}

function handleFileSelect(e) {
  const file = e.target.files[0]
  if (file) {
    testImageName.value = file.name
    testImage.value = URL.createObjectURL(file)
  }
}

function handleDrop(e) {
  const file = e.dataTransfer.files[0]
  if (file && file.type.startsWith('image/')) {
    testImageName.value = file.name
    testImage.value = URL.createObjectURL(file)
  }
}

async function doTestModel() {
  if (!testImage.value) return

  testing.value = true
  testResult.value = null

  // ✅ 修复：使用 Vue ref 替代 document.querySelector
  const formData = new FormData()
  if (fileInput.value && fileInput.value.files[0]) {
    formData.append('image', fileInput.value.files[0])
  }

  try {
    const result = await testModel(formData)
    testResult.value = result
  } catch (e) {
    console.error('模型测试失败:', e)
    alert('模型测试失败: ' + (e.message || '未知错误'))
  } finally {
    testing.value = false
  }
}

async function doBatchTest() {
  if (!testImage.value) return

  testing.value = true
  batchResults.value = []

  // ✅ 修复：使用 Vue ref
  const file = fileInput.value?.files?.[0]
  if (!file) return

  for (let i = 0; i < batchCount.value; i++) {
    const formData = new FormData()
    formData.append('image', file)

    try {
      const result = await testModel(formData)
      batchResults.value.push(result)
    } catch (e) {
      console.error(`批量测试 ${i + 1}/${batchCount.value} 失败:`, e)
    }
  }

  testing.value = false
  alert(`批量测试完成：${batchResults.value.length}/${batchCount.value} 次`)
}

async function loadReviewItems() {
  try {
    const params = reviewStatusFilter.value ? { review_status: reviewStatusFilter.value } : {}
    const result = await getAdminReviewItems(params)
    reviewItems.value = result.items || []
  } catch (e) {
    console.error('加载审核列表失败:', e)
  }
}

async function confirmForceDelist(item) {
  if (!confirm(`确定要强制下架商品「${item.ai_generated_title}」吗？`)) return

  const reason = prompt('请输入下架原因（用户将收到此通知）:', '商品经管理员审核不符合平台规范，请修改后重新发布')
  if (!reason) return

  try {
    await forceDelistItem(item.id, reason)
    loadReviewItems()
    alert('✅ 商品已强制下架，用户已收到通知')
  } catch (e) {
    alert('❌ 操作失败: ' + (e.message || '未知错误'))
  }
}

async function loadModelMetrics() {
  try {
    const result = await getCheckpointMetrics()
    if (result.success && result.models) {
      yoloMetrics.value = result.models.yolo || { error: '无数据' }
      defectMetrics.value = result.models.defect || { error: '无数据' }
    }
  } catch (e) {
    console.error('加载模型指标失败:', e)
  }
}

async function loadHardCases() {
  try {
    const result = await getAdminHardCases({ is_fixed: casesFilter.value })
    hardCases.value = result.cases || []
  } catch (e) {
    console.error('加载错误案例失败:', e)
  }
}

async function markCaseFixed(caseId) {
  try {
    await markHardCaseFixed(caseId)
    loadHardCases()
    alert('✅ 错误案例已标记为已修复')
  } catch (e) {
    alert('❌ 操作失败: ' + (e.message || '未知错误'))
  }
}

// ==================== Users ====================

async function loadUsers() {
  try {
    const result = await getAdminUsers()
    adminUsers.value = result.users || []
  } catch (e) { console.error('加载用户失败:', e) }
}

async function addUser() {
  if (!newUsername.value || !newPassword.value) return
  try {
    await createAdminUser(newUsername.value.trim(), newPassword.value, newUserRole.value)
    newUsername.value = ''
    newPassword.value = ''
    loadUsers()
    loadStats()
  } catch (e) { alert('添加失败: ' + (e?.response?.data?.detail || e.message)) }
}

async function deleteUser(u) {
  if (!confirm(`确定要删除用户「${u.username}」吗？此操作不可恢复。`)) return
  try {
    await deleteAdminUser(u.id)
    loadUsers()
    loadStats()
  } catch (e) { alert('删除失败: ' + (e?.response?.data?.detail || e.message)) }
}

async function toggleUser(u) {
  const action = u.status === 'active' ? '禁用' : '启用'
  if (!confirm(`确定要${action}用户「${u.username}」吗？${u.status === 'active' ? '禁用后该用户将无法登录。' : ''}`)) return
  try {
    await toggleUserStatus(u.id)
    loadUsers()
  } catch (e) { alert('操作失败: ' + (e?.response?.data?.detail || e.message)) }
}

async function doSyncQdrant() {
  try {
    const result = await syncQdrant()
    alert(`同步完成！总数: ${result.total}, 已索引: ${result.indexed}, 失败: ${result.failed}`)
    loadStats()
  } catch (e) { alert('同步失败: ' + (e?.response?.data?.detail || e.message)) }
}

// ==================== Lifecycle ====================

watch(activeTab, (tab) => {
  if (tab === 'stats') loadStats()
  else if (tab === 'review') loadReviewItems()
  else if (tab === 'metrics') loadModelMetrics()
  else if (tab === 'cases') loadHardCases()
  else if (tab === 'users') loadUsers()
})

onMounted(() => {
  loadStats()
  loadReviewItems()
  loadModelMetrics()
  loadHardCases()
  loadUsers()
})
</script>

<style scoped>
.input-field-sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.8125rem;
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  background: white;
  outline: none;
}
.input-field-sm:focus {
  border-color: var(--color-primary-400);
  box-shadow: 0 0 0 3px var(--color-primary-100);
}
</style>
