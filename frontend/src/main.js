import { createApp } from 'vue'
import { createPinia } from 'pinia'
// 阶段四：Element Plus 改为按需引入（组件由 unplugin 自动注册）
// 函数式 API（ElMessage/ElMessageBox/v-loading）的样式需手动引入
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'
import 'element-plus/es/components/loading/style/css'
import '@/styles/index.scss'

import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
