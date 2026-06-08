import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useDetectStore = defineStore('detect', () => {
  const currentResult = ref(null)
  const isProcessing = ref(false)
  const error = ref(null)

  function setResult(result) {
    currentResult.value = result
    error.value = null
  }

  function clearResult() {
    currentResult.value = null
    error.value = null
  }

  function setError(msg) {
    error.value = msg
    currentResult.value = null
  }

  return { currentResult, isProcessing, error, setResult, clearResult, setError }
})
