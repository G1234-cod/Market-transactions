<template>
  <div class="space-y-10 relative">
    <div class="hero-section relative py-12 sm:py-16 overflow-hidden">
      <div class="orb orb-primary w-72 h-72 -top-5 -right-5 animate-float-slow"></div>
      <div class="orb orb-accent w-56 h-56 bottom-0 -left-5 animate-float-medium"></div>
      
      <div class="relative z-10">
        <div class="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div>
            <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-medium mb-4 animate-fade-in-up-1">
              <span class="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
              管理员权限
            </div>
            
            <h1 class="text-4xl sm:text-5xl font-extrabold gradient-text animate-fade-in-up-2">管理员控制台</h1>
            <p class="text-text-secondary text-base mt-3 max-w-lg animate-fade-in-up-3">管理平台数据、测试模型效果、审核商品</p>
          </div>
          
          <div class="badge badge-warning px-4 py-2 text-sm animate-fade-in-up-4">管理员</div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 animate-fade-in-up-2">
      <div class="stat-card cursor-pointer card-glow-hover hover:-translate-y-2 transition-all" @click="activeTab = 'users'">
        <div class="w-12 h-12 mx-auto mb-4 rounded-xl bg-gradient-to-br from-primary-500/20 to-primary-600/20 flex items-center justify-center">
          <span class="text-primary-400 text-xl">👤</span>
        </div>
        <div class="stat-value text-primary-400 text-4xl">{{ stats.overview?.users || 0 }}</div>
        <div class="stat-label text-sm">注册用户</div>
      </div>
      <div class="stat-card cursor-pointer card-glow-hover hover:-translate-y-2 transition-all" @click="activeTab = 'review'">
        <div class="w-12 h-12 mx-auto mb-4 rounded-xl bg-gradient-to-br from-accent-500/20 to-accent-600/20 flex items-center justify-center">
          <span class="text-accent-400 text-xl">📦</span>
        </div>
        <div class="stat-value text-accent-400 text-4xl">{{ stats.overview?.published_items || 0 }}</div>
        <div class="stat-label text-sm">已发布商品</div>
      </div>
      <div class="stat-card cursor-pointer card-glow-hover hover:-translate-y-2 transition-all" @click="activeTab = 'cases'">
        <div class="w-12 h-12 mx-auto mb-4 rounded-xl bg-gradient-to-br from-amber-500/20 to-amber-600/20 flex items-center justify-center">
          <span class="text-amber-400 text-xl">🔧</span>
        </div>
        <div class="stat-value text-amber-400 text-4xl">{{ stats.model_performance?.hard_cases?.unfixed || 0 }}</div>
        <div class="stat-label text-sm">待修复错误案例</div>
      </div>
    </div>

    <div class="flex flex-wrap gap-3 mb-8 animate-fade-in-up-3">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="pill-button px-5 py-2.5 text-sm ripple-container"
        :class="activeTab === tab.id ? 'pill-button-active' : 'pill-button-inactive'"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <transition name="page" mode="out-in">
      <div :key="activeTab">
      <!-- ==================== 数据概览 ==================== -->
      <div v-if="activeTab === 'stats'" class="space-y-8">
        <div class="glass-card card-glow-hover">
          <div class="bg-gradient-to-r from-primary-500/15 via-accent-500/10 to-primary-500/15 px-8 py-5 border-b border-border/50">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-bold text-text-primary">📊 系统数据概览</h2>
            <button @click="doSyncQdrant" class="px-4 py-2 rounded-xl text-xs font-medium bg-accent-500/15 text-accent-400 border border-accent-500/30 hover:bg-accent-500/25 transition-all ripple-container">
              🔄 同步向量库
            </button>
          </div>
        </div>
          <div class="p-8">
            <div class="grid grid-cols-2 md:grid-cols-3 gap-5 mb-8">
              <div class="bg-space-lighter/50 rounded-2xl p-5 card-glow-hover">
                <div class="text-3xl font-bold text-text-primary">{{ stats.overview?.total_items || 0 }}</div>
                <div class="text-sm text-text-muted mt-1">商品总数</div>
              </div>
              <div class="bg-space-lighter/50 rounded-2xl p-5 card-glow-hover">
                <div class="text-3xl font-bold text-accent-400">{{ stats.overview?.sold_items || 0 }}</div>
                <div class="text-sm text-text-muted mt-1">已售出</div>
              </div>
              <div class="bg-space-lighter/50 rounded-2xl p-5 card-glow-hover">
                <div class="text-3xl font-bold text-text-primary">{{ stats.overview?.categories || 0 }}</div>
                <div class="text-sm text-text-muted mt-1">品类数</div>
              </div>
              <div class="bg-space-lighter/50 rounded-2xl p-5 card-glow-hover">
                <div class="text-3xl font-bold text-text-primary">{{ stats.overview?.brands || 0 }}</div>
                <div class="text-sm text-text-muted mt-1">品牌数</div>
              </div>
              <div class="bg-space-lighter/50 rounded-2xl p-5 card-glow-hover">
                <div class="text-3xl font-bold text-text-primary">{{ stats.overview?.audit_logs || 0 }}</div>
                <div class="text-sm text-text-muted mt-1">审计日志</div>
              </div>
              <div class="bg-space-lighter/50 rounded-2xl p-5 card-glow-hover">
                <div class="text-3xl font-bold text-text-primary">{{ stats.overview?.notifications || 0 }}</div>
                <div class="text-sm text-text-muted mt-1">通知数</div>
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
                    <span class="font-semibold text-accent-400">{{ stats.model_performance?.hard_cases?.fixed || 0 }}</span>
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-sm text-text-muted">待修复</span>
                    <span class="font-semibold text-amber-400">{{ stats.model_performance?.hard_cases?.unfixed || 0 }}</span>
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
          <div class="bg-gradient-to-r from-primary-500/10 to-accent-500/10 px-6 py-4 border-b border-border/50">
          <h2 class="font-semibold text-text-primary">🧪 模型测试</h2>
        </div>
          <div class="p-6">
            <div
              class="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-primary-500/50 transition-colors cursor-pointer"
              @click="$refs.fileInput.click()" @dragover.prevent @drop.prevent="handleDrop"
            >
              <div v-if="!testImage" class="space-y-3">
                <div class="text-4xl">📷</div>
                <p class="text-text-muted">点击或拖拽上传图片进行模型测试</p>
                <p class="text-xs text-text-muted">支持 JPG、PNG 格式 · 可连续上传测试多张</p>
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
            <div v-if="batchResults.length > 0" class="mt-4 glass-card p-4 bg-accent-500/10">
              <h3 class="text-sm font-semibold text-accent-400 mb-3">📊 批量测试结果</h3>
              <div class="grid grid-cols-4 gap-3 text-center">
                <div>
                  <div class="text-xl font-bold text-text-primary">{{ batchResults.length }}</div>
                  <div class="text-xs text-text-muted">总测试数</div>
                </div>
                <div>
                  <div class="text-xl font-bold text-accent-400">{{ batchAgreeCount }}</div>
                  <div class="text-xs text-text-muted">模型一致</div>
                </div>
                <div>
                  <div class="text-xl font-bold text-amber-400">{{ batchDisagreeCount }}</div>
                  <div class="text-xs text-text-muted">模型不一致</div>
                </div>
                <div>
                  <div class="text-xl font-bold text-text-primary">{{ batchAgreementRate }}%</div>
                  <div class="text-xs text-text-muted">一致率</div>
                </div>
              </div>
              <button class="btn-secondary-sm mt-3 ripple-container" @click="batchResults = []">清除结果</button>
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
              <div v-if="testResult.model_comparison?.has_disagreement" class="glass-card bg-amber-500/10">
                <div class="px-4 py-3 border-b border-amber-500/30">
                  <h3 class="font-semibold text-sm text-amber-400">⚠️ 模型结果不一致</h3>
                </div>
                <div class="p-4">
                  <div class="grid grid-cols-2 gap-4">
                    <div class="bg-space-lighter/50 rounded-lg p-3">
                      <div class="text-xs text-text-muted mb-1">自研YOLO模型</div>
                      <div class="font-semibold text-text-primary">{{ testResult.model_comparison?.yolo?.category || '-' }}</div>
                      <div class="text-xs text-text-muted">置信度: {{ (testResult.model_comparison?.yolo?.confidence * 100)?.toFixed(1) || 0 }}%</div>
                    </div>
                    <div class="bg-space-lighter/50 rounded-lg p-3">
                      <div class="text-xs text-text-muted mb-1">阿里云Qwen模型</div>
                      <div class="font-semibold text-text-primary">{{ testResult.model_comparison?.qwen?.category || '-' }}</div>
                      <div class="text-xs text-text-muted">品牌: {{ testResult.model_comparison?.qwen?.brand || '-' }}</div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 瑕疵检测结果（含标注图） -->
              <div v-if="testResult.defect_result?.defect_count > 0" class="glass-card">
                <div class="px-4 py-3 border-b border-border/50 bg-gradient-to-r from-danger-500/10 to-amber-500/10">
                  <h3 class="font-semibold text-sm text-danger-400">🔍 瑕疵检测结果</h3>
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
                        <div class="text-3xl font-bold text-danger-400">{{ testResult.defect_result.defect_count }}</div>
                        <div>
                          <div class="text-sm text-text-muted">处瑕疵</div>
                          <div class="text-xs text-text-muted">详见下方标签</div>
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
          <div class="bg-gradient-to-r from-primary-500/10 to-accent-500/10 px-6 py-4 border-b border-border/50 flex items-center justify-between flex-wrap gap-3">
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
        <div class="glass-card">
          <div class="bg-gradient-to-r from-primary-500/10 to-accent-500/10 px-6 py-4 border-b border-border/50">
            <h2 class="font-semibold text-text-primary">📈 模型训练指标</h2>
          </div>
          <div class="p-6">
            <div class="flex items-center justify-between mb-4">
              <div>
                <div class="text-3xl font-bold text-primary-400">{{ (modelMetricsStats.avg_accuracy * 100)?.toFixed(2) || '0.00' }}%</div>
                <div class="text-xs text-text-muted">平均准确率</div>
              </div>
              <div>
                <div class="text-3xl font-bold text-accent-400">{{ (modelMetricsStats.avg_f1 * 100)?.toFixed(2) || '0.00' }}%</div>
                <div class="text-xs text-text-muted">平均F1分数</div>
              </div>
              <div>
                <div class="text-3xl font-bold text-text-primary">{{ modelMetricsStats.total || 0 }}</div>
                <div class="text-xs text-text-muted">训练次数</div>
              </div>
            </div>

            <div v-if="modelMetrics.length > 0" class="space-y-3 max-h-96 overflow-y-auto">
              <div v-for="metric in modelMetrics" :key="metric.id" class="bg-space-lighter/50 rounded-xl p-4">
                <div class="flex items-center justify-between mb-2">
                  <span class="font-medium text-sm">{{ metric.model_name === 'yolo' ? '分类模型 (YOLO)' : '瑕疵检测模型' }}</span>
                  <span class="text-xs text-text-muted">{{ formatDate(metric.training_date) }}</span>
                </div>
                <div class="grid grid-cols-4 gap-4">
                  <div>
                    <div class="text-sm font-semibold">{{ metric.accuracy ? (metric.accuracy * 100).toFixed(2) + '%' : '-' }}</div>
                    <div class="text-xs text-text-muted">准确率</div>
                  </div>
                  <div>
                    <div class="text-sm font-semibold">{{ metric.precision ? (metric.precision * 100).toFixed(2) + '%' : '-' }}</div>
                    <div class="text-xs text-text-muted">精确率</div>
                  </div>
                  <div>
                    <div class="text-sm font-semibold">{{ metric.recall ? (metric.recall * 100).toFixed(2) + '%' : '-' }}</div>
                    <div class="text-xs text-text-muted">召回率</div>
                  </div>
                  <div>
                    <div class="text-sm font-semibold">{{ metric.f1_score ? (metric.f1_score * 100).toFixed(2) + '%' : '-' }}</div>
                    <div class="text-xs text-text-muted">F1分数</div>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="text-center py-8 text-text-muted">
              <div class="text-4xl mb-2">📊</div>
              <p>暂无训练指标数据</p>
            </div>
          </div>
        </div>

        <!-- 触发模型训练 -->
        <div class="glass-card">
          <div class="bg-gradient-to-r from-primary-500/10 to-accent-500/10 px-6 py-4 border-b border-border/50 flex items-center justify-between">
            <h2 class="font-semibold text-text-primary">⚙️ 模型训练</h2>
            <div class="flex items-center gap-2">
              <span v-if="weeklySchedulerRunning" class="text-xs text-accent-600 flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-accent-500 animate-pulse"></span> 每周自动训练运行中</span>
              <span v-else class="text-xs text-text-muted">调度器待启动</span>
            </div>
          </div>
          <div class="p-6">
            <div class="space-y-4">
              <div class="flex gap-4">
                <select v-model="trainingModel" class="input-field flex-1">
                  <option value="yolo">分类模型 (YOLO)</option>
                  <option value="defect">瑕疵检测模型</option>
                </select>
                <select v-model="trainingEpochs" class="input-field w-32">
                  <option :value="5">5 轮</option>
                  <option :value="10">10 轮</option>
                  <option :value="20">20 轮</option>
                  <option :value="30">30 轮</option>
                  <option :value="50">50 轮</option>
                </select>
              </div>
              <button
                class="btn-primary w-full"
                :disabled="training || hasRunningJob"
                @click="triggerTraining"
              >
                <span v-if="training" class="loading-spinner mr-2" />
                <span>{{ training ? '启动中...' : hasRunningJob ? '训练进行中...' : '🚀 触发训练' }}</span>
              </button>

              <!-- ✅ 训练进度条 -->
              <div v-if="activeJobs.length" class="space-y-3">
                <div v-for="job in activeJobs" :key="job.job_id" class="rounded-xl border border-primary-500/30 bg-primary-500/10 p-4">
                  <div class="flex items-center justify-between mb-2">
                    <span class="text-sm font-semibold text-primary-400">{{ job.model_name === 'yolo' ? '分类模型' : '瑕疵模型' }} 训练中</span>
                    <span class="text-xs text-primary-400">{{ job.progress }}%</span>
                  </div>
                  <div class="w-full h-3 bg-primary-200 rounded-full overflow-hidden">
                    <div class="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full transition-all duration-1000"
                      :style="{ width: job.progress + '%' }" />
                  </div>
                  <p class="text-xs text-text-muted mt-2">轮数: {{ job.epochs }} | 启动: {{ job.started_at?.slice(11,19) }}</p>
                </div>
              </div>

              <div v-if="trainingResult" class="rounded-xl p-4"
                :class="trainingResult.success ? 'bg-accent-500/10' : 'bg-danger-500/10'">
                <p class="text-sm" :class="trainingResult.success ? 'text-accent-400' : 'text-danger-400'">
                  {{ trainingResult.message || (trainingResult.success ? '训练已启动' : '训练失败') }}
                </p>
              </div>

              <!-- ✅ 最近完成 -->
              <div v-if="recentJobs.length" class="text-xs text-text-muted space-y-1">
                <p class="font-medium">最近训练记录：</p>
                <div v-for="job in recentJobs" :key="job.job_id" class="flex items-center gap-2">
                  <span :class="job.status === 'completed' ? 'text-accent-600' : 'text-danger-600'">
                    {{ job.status === 'completed' ? '✅' : '❌' }}
                  </span>
                  <span>{{ job.model_name }}</span>
                  <span>{{ job.started_at?.slice(0,16) }}</span>
                </div>
              </div>

              <!-- 训练计划提示 -->
              <div class="bg-space-lighter/50 rounded-xl p-4 text-xs text-text-muted">
                <p class="font-medium mb-2">📅 训练计划：</p>
                <ul class="list-disc list-inside space-y-1">
                  <li>✅ 每周一凌晨2点自动训练（已启用）</li>
                  <li>手动训练：积累错误案例后随时触发</li>
                  <li>差异数据积累到 50+ 条后建议重新训练</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ==================== 错误案例 ==================== -->
      <div v-else-if="activeTab === 'cases'" key="cases" class="space-y-6">
        <div class="glass-card">
          <div class="bg-gradient-to-r from-primary-500/10 to-accent-500/10 px-6 py-4 border-b border-border/50 flex items-center justify-between">
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
          <div class="bg-gradient-to-r from-primary-500/10 to-accent-500/10 px-6 py-4 border-b border-border/50 flex items-center justify-between">
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
              <div v-for="u in adminUsers" :key="u.id" class="flex items-center justify-between px-4 py-3 border border-border/50 rounded-xl hover:bg-space-lighter/50 transition-colors">
                <div class="flex items-center gap-4">
                  <span class="font-medium text-text-primary">{{ u.username }}</span>
                  <span class="text-xs px-2 py-0.5 rounded-full" :class="u.role === 'admin' ? 'bg-amber-500/20 text-amber-400' : 'bg-primary-500/20 text-primary-400'">{{ u.role }}</span>
                  <span class="text-xs px-2 py-0.5 rounded-full" :class="u.status === 'active' ? 'bg-success-500/20 text-success-400' : 'bg-danger-500/20 text-danger-400'">{{ u.status === 'active' ? '正常' : '已禁用' }}</span>
                  <span class="text-xs text-text-muted">{{ u.created_at?.slice(0,10) }}</span>
                </div>
                <div class="flex items-center gap-2">
                  <button @click="toggleUser(u)" class="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ripple-container"
                    :class="u.status === 'active' ? 'bg-danger-500/10 text-danger-400 border border-danger-500/30 hover:bg-danger-500/20' : 'bg-success-500/10 text-success-400 border border-success-500/30 hover:bg-success-500/20'">
                    {{ u.status === 'active' ? '🔒 禁用' : '🔓 启用' }}
                  </button>
                  <button @click="deleteUser(u)" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-danger-500/10 text-danger-400 border border-danger-500/30 hover:bg-danger-500/20 ripple-container">🗑 删除</button>
                </div>
              </div>
              <div v-if="!adminUsers.length" class="text-center py-8 text-text-muted">暂无用户</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ==================== 品类管理 ==================== -->
      <div v-if="activeTab === 'categories'" key="categories" class="space-y-6">
        <div class="glass-card">
          <div class="bg-gradient-to-r from-primary-500/10 to-accent-500/10 px-6 py-4 border-b border-border/50 flex items-center justify-between">
            <h2 class="font-semibold text-text-primary">🏷️ 品类品牌管理</h2>
            <span class="text-xs text-text-muted">{{ categoryBrandList.length }} 个品牌 · {{ Object.keys(groupedCategories).length }} 大类</span>
          </div>
          <div class="p-6">
            <!-- 新增 -->
            <div class="flex gap-3 mb-6">
              <input v-model="newCategory" placeholder="大类（如：耳机）" class="input-field flex-1" />
              <input v-model="newBrand" placeholder="品牌（如：华为）" class="input-field flex-1" />
              <button class="btn-primary-sm whitespace-nowrap" @click="addCategoryBrand" :disabled="!newCategory || !newBrand">
                ➕ 添加
              </button>
            </div>
            <!-- 列表 -->
            <div v-if="Object.keys(groupedCategories).length" class="space-y-4">
              <div v-for="(brands, cat) in groupedCategories" :key="cat" class="border border-border rounded-xl overflow-hidden">
                <div class="bg-space-lighter/50 px-4 py-2.5 flex items-center justify-between">
                  <span class="font-semibold text-text-primary text-sm">{{ cat }}</span>
                  <span class="text-xs text-text-muted">{{ brands.length }} 个品牌</span>
                </div>
                <div class="p-3 flex flex-wrap gap-2">
                  <span v-for="b in brands" :key="b" class="px-2.5 py-1 rounded-lg text-xs font-medium bg-space-card border border-border text-text-secondary">
                    {{ b }}
                  </span>
                </div>
              </div>
            </div>
            <div v-else class="text-center py-8 text-text-muted">暂无数据</div>
          </div>
        </div>
      </div>
      </div>
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
  getAdminModelMetrics,
  triggerModelTraining,
  getTrainingStatus,
  getAdminUsers,
  createAdminUser,
  deleteAdminUser,
  toggleUserStatus,
  getAdminCategories,
  addAdminCategory,
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
  { id: 'categories', label: '🏷️ 品类管理' },
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
const modelMetrics = ref([])
const modelMetricsStats = ref({})
const trainingModel = ref('yolo')
const trainingEpochs = ref(10)
const training = ref(false)
const trainingResult = ref(null)
// ✅ 训练进度追踪
const activeJobs = ref([])
const recentJobs = ref([])
const hasRunningJob = ref(false)
const weeklySchedulerRunning = ref(false)
let _trainingPollTimer = 0

// ==================== Users ====================
const adminUsers = ref([])
const newUsername = ref('')
const newPassword = ref('')
const newUserRole = ref('user')

// ==================== Categories ====================
const categoryBrandList = ref([])
const groupedCategories = ref({})
const newCategory = ref('')
const newBrand = ref('')

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
    const result = await getAdminModelMetrics()
    modelMetrics.value = result.metrics || []
    modelMetricsStats.value = result.stats || {}
  } catch (e) {
    console.error('加载模型指标失败:', e)
  }
}

async function triggerTraining() {
  training.value = true
  trainingResult.value = null

  try {
    trainingResult.value = await triggerModelTraining(trainingModel.value, trainingEpochs.value)
    if (trainingResult.value.success) {
      startTrainingPolling()
    }
    setTimeout(loadModelMetrics, 2000)
  } catch (e) {
    console.error('触发训练失败:', e)
    trainingResult.value = { success: false, message: '训练失败: ' + (e.message || '未知错误') }
  } finally {
    training.value = false
  }
}

// ✅ 轮询训练状态（每10秒）
async function pollTrainingStatus() {
  try {
    const result = await getTrainingStatus()
    activeJobs.value = result.active_jobs || []
    recentJobs.value = result.recent_jobs || []
    hasRunningJob.value = result.has_running || false
    weeklySchedulerRunning.value = true  // 调度器随服务启动
  } catch (e) {
    console.error('轮询训练状态失败:', e)
  }
}

function startTrainingPolling() {
  clearInterval(_trainingPollTimer)
  pollTrainingStatus()
  _trainingPollTimer = setInterval(pollTrainingStatus, 10000)
}

function stopTrainingPolling() {
  clearInterval(_trainingPollTimer)
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

// ==================== Categories ====================

async function loadCategories() {
  try {
    const result = await getAdminCategories()
    if (result.success) {
      categoryBrandList.value = result.category_brands || {}
      // Group by category
      const grouped = {}
      for (const [cat, brands] of Object.entries(result.category_brands || {})) {
        grouped[cat] = brands
      }
      groupedCategories.value = grouped
    }
  } catch (e) {
    console.error('加载品类失败:', e)
  }
}

async function addCategoryBrand() {
  if (!newCategory.value || !newBrand.value) return
  try {
    await addAdminCategory(newCategory.value.trim(), newBrand.value.trim())
    newCategory.value = ''
    newBrand.value = ''
    loadCategories()
    loadStats()
  } catch (e) {
    alert('添加失败: ' + (e?.response?.data?.detail || e.message || '未知错误'))
  }
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
  else if (tab === 'metrics') { loadModelMetrics(); startTrainingPolling() }
  else if (tab === 'categories') loadCategories()
  stopTrainingPolling()
  if (tab === 'stats') loadStats()
  else if (tab === 'review') loadReviewItems()
  else if (tab === 'metrics') { loadModelMetrics(); startTrainingPolling() }
  else if (tab === 'cases') loadHardCases()
  else if (tab === 'users') loadUsers()
  else if (tab === 'categories') loadCategories()
})

onMounted(() => {
  loadStats()
  loadReviewItems()
  loadModelMetrics()
  loadHardCases()
  loadUsers()
  loadCategories()
  pollTrainingStatus()  // 初始化训练状态
})
</script>

<style scoped>
</style>
