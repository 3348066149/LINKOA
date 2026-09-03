<template>
  <div class="ai-config">
    <el-card shadow="never">
      <template #header>
        <div class="card-head">
          <span class="card-title">AI 助手设置</span>
          <span class="card-tip">配置青青侠的大模型接入与人格设定，保存后即时生效</span>
        </div>
      </template>

      <el-form :model="form" label-width="110px" class="config-form" @submit.prevent>
        <el-form-item label="AI 人设">
          <el-input
            v-model="form.systemPrompt"
            type="textarea"
            :rows="6"
            placeholder="填写青青侠的人格设定、职责边界与回答要求"
          />
        </el-form-item>

        <el-form-item label="模型名称">
          <el-input v-model="form.model" placeholder="如 deepseek-chat、deepseek-reasoner" />
        </el-form-item>

        <el-form-item label="API Key">
          <el-input v-model="form.apiKey" placeholder="填写模型服务商的 API Key">
            <template #append>留空不修改</template>
          </el-input>
          <div class="form-tip">已保存的 Key 会脱敏显示（如 sk-4b****e2），输入新值才会更新</div>
        </el-form-item>

        <el-form-item label="接口地址">
          <el-input v-model="form.baseUrl" placeholder="https://api.deepseek.com" />
          <div class="form-tip">支持 OpenAI 兼容接口，可切换其他模型服务商</div>
        </el-form-item>

        <el-form-item label="温度">
          <el-slider v-model="form.temperature" :min="0" :max="2" :step="0.1" show-input />
        </el-form-item>

        <el-form-item label="最大 Token">
          <el-input-number v-model="form.maxTokens" :min="1" :max="32768" :step="256" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="save">保存设置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getAiConfig, updateAiConfig } from '@/api/ai'

const form = reactive({
  systemPrompt: '',
  model: '',
  apiKey: '',
  baseUrl: '',
  temperature: 0.7,
  maxTokens: 2048,
})

const saving = ref(false)

async function load() {
  const data = await getAiConfig()
  form.systemPrompt = data.systemPrompt || ''
  form.model = data.model || ''
  form.apiKey = data.apiKey || ''
  form.baseUrl = data.baseUrl || ''
  form.temperature = data.temperature ?? 0.7
  form.maxTokens = data.maxTokens ?? 2048
}

async function save() {
  saving.value = true
  try {
    await updateAiConfig({
      systemPrompt: form.systemPrompt,
      model: form.model,
      apiKey: form.apiKey,
      baseUrl: form.baseUrl,
      temperature: form.temperature,
      maxTokens: form.maxTokens,
    })
    ElMessage.success('AI 设置已保存')
    await load()
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.ai-config {
  padding: 4px 0;
}
.card-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
}
.card-title { font-size: 16px; font-weight: 600; color: var(--lk-text-1, #303133); }
.card-tip { font-size: 13px; color: var(--lk-text-3, #6f737a); }
.config-form { max-width: 640px; }
.form-tip {
  font-size: 12px;
  color: var(--lk-text-3, #6f737a);
  line-height: 1.5;
  margin-top: 4px;
}
</style>
