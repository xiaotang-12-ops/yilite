import { defineStore } from 'pinia'
import { ref } from 'vue'

const ADMIN_STATUS_KEY = 'isAdmin'

export const useAdminStore = defineStore('admin', () => {
  const isAdmin = ref(false)

  const ensureInit = () => {
    if (typeof window === 'undefined') return
    isAdmin.value = sessionStorage.getItem(ADMIN_STATUS_KEY) === 'true'
  }

  const login = () => {
    isAdmin.value = true
    sessionStorage.setItem(ADMIN_STATUS_KEY, 'true')
  }

  const logout = () => {
    isAdmin.value = false
    sessionStorage.removeItem(ADMIN_STATUS_KEY)
  }

  return {
    isAdmin,
    ensureInit,
    login,
    logout
  }
})
