/**
 * 响应式断点检测 composable
 * 用法：const { isMobile } = useIsMobile(768)
 * 基于 matchMedia，避免 resize 频繁触发；SSR 安全（默认 false，mounted 后修正）。
 */
import { ref, onMounted, onBeforeUnmount } from 'vue'

export function useIsMobile(breakpoint = 768) {
  const isMobile = ref(false)
  let mql = null

  function update(e) {
    if (e && typeof e.matches === 'boolean') {
      isMobile.value = e.matches
    } else {
      isMobile.value = window.innerWidth < breakpoint
    }
  }

  onMounted(() => {
    mql = window.matchMedia(`(max-width: ${breakpoint - 1}px)`)
    update(mql)
    if (typeof mql.addEventListener === 'function') {
      mql.addEventListener('change', update)
    } else if (typeof mql.addListener === 'function') {
      mql.addListener(update) // 兼容旧浏览器
    }
  })

  onBeforeUnmount(() => {
    if (mql) {
      if (typeof mql.removeEventListener === 'function') {
        mql.removeEventListener('change', update)
      } else if (typeof mql.removeListener === 'function') {
        mql.removeListener(update)
      }
    }
  })

  return { isMobile }
}
