import { createApp } from 'vue'
import ArcoVue from '@arco-design/web-vue'
import ArcoVueIcon from '@arco-design/web-vue/es/icon'
import '@arco-design/web-vue/dist/arco.css'

import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'

import './styles/soft-design.css'
import './styles/animations.css'
import './styles/query-page-optimized.css'
import './style.css'

const app = createApp(App)

app.use(ArcoVue)
app.use(ArcoVueIcon)
app.use(router)
app.use(createPinia())

app.mount('#app')
