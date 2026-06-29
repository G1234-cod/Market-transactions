<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold gradient-text">消息通知</h1>
        <p class="text-text-muted text-sm mt-1">查看平台通知和商品审核状态</p>
      </div>
      <button 
        v-if="unreadCount > 0"
        class="btn-secondary-sm"
        @click="markAllRead"
      >
        全部已读
      </button>
    </div>

    <div v-if="notifications.length === 0" class="glass-card text-center py-16">
      <div class="text-6xl mb-4">📭</div>
      <h3 class="text-lg font-semibold text-text-primary mb-2">暂无消息</h3>
      <p class="text-text-muted">您还没有收到任何通知</p>
    </div>

    <div v-else class="space-y-4">
      <div 
        v-for="notification in notifications" 
        :key="notification.id"
        class="glass-card p-4 cursor-pointer transition-all"
        :class="notification.is_read ? 'opacity-70' : 'bg-primary-50/50'"
        @click="markAsRead(notification.id)"
      >
        <div class="flex gap-4">
          <div class="w-12 h-12 rounded-full flex items-center justify-center text-xl"
            :class="getIconBgClass(notification.type)">
            {{ getIcon(notification.type) }}
          </div>
          <div class="flex-1">
            <div class="flex items-start justify-between">
              <div>
                <h3 class="font-semibold text-text-primary">{{ notification.title }}</h3>
                <p class="text-sm text-text-secondary mt-1">{{ notification.message }}</p>
              </div>
              <span v-if="!notification.is_read" class="w-2 h-2 bg-primary-500 rounded-full mt-2"></span>
            </div>
            <div class="flex items-center gap-4 mt-2 text-xs text-text-muted">
              <span>{{ formatDate(notification.created_at) }}</span>
              <span v-if="notification.item_id" class="badge badge-primary">商品ID: {{ notification.item_id }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { getNotifications, markNotificationRead, markAllNotificationsRead } from '../api/index.js'

const notifications = ref([])

const unreadCount = computed(() => {
  return notifications.value.filter(n => !n.is_read).length
})

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

function getIcon(type) {
  switch (type) {
    case 'force_delisted': return '⚠️'
    case 'review_required': return '🔍'
    case 'system': return '📢'
    default: return '📩'
  }
}

function getIconBgClass(type) {
  switch (type) {
    case 'force_delisted': return 'bg-danger-100'
    case 'review_required': return 'bg-warning-100'
    case 'system': return 'bg-primary-100'
    default: return 'bg-surface-secondary'
  }
}

async function loadNotifications() {
  try {
    const result = await getNotifications()
    notifications.value = result.notifications || []
  } catch (e) {
    console.error('加载通知失败:', e)
  }
}

async function markAsRead(id) {
  try {
    await markNotificationRead(id)
    const notification = notifications.value.find(n => n.id === id)
    if (notification) {
      notification.is_read = true
    }
  } catch (e) {
    console.error('标记已读失败:', e)
  }
}

async function markAllRead() {
  try {
    await markAllNotificationsRead()
    notifications.value.forEach(n => n.is_read = true)
  } catch (e) {
    console.error('全部已读失败:', e)
  }
}

onMounted(() => {
  loadNotifications()
})
</script>
