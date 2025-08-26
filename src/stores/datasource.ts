import { defineStore } from 'pinia'
import { ref, computed, readonly } from 'vue'
import { dataSourceApi } from '@/api/datasource'
import type { DataSource, CreateDataSourceForm, UpdateDataSourceForm } from '@/types/datasource'

export const useDataSourceStore = defineStore('datasource', () => {
  const dataSources = ref<DataSource[]>([])
  const currentDataSource = ref<DataSource | null>(null)
  const isLoading = ref(false)
  const isCreating = ref(false)
  const isUpdating = ref(false)
  const isDeleting = ref(false)

  // 计算属性
  const dataSourcesByType = computed(() => {
    const groups: Record<string, DataSource[]> = {}
    dataSources.value.forEach(ds => {
      if (!groups[ds.type]) {
        groups[ds.type] = []
      }
      groups[ds.type].push(ds)
    })
    return groups
  })

  const totalCount = computed(() => dataSources.value.length)
  
  const typeStatistics = computed(() => {
    const stats: Record<string, number> = {}
    dataSources.value.forEach(ds => {
      stats[ds.type] = (stats[ds.type] || 0) + 1
    })
    return stats
  })

  // 获取数据源列表
  const fetchDataSources = async () => {
    isLoading.value = true
    try {
      const response = await dataSourceApi.getDataSources()
      console.log('📊 DataSource Store: API响应', response)
      
      // 处理分页响应结构：response可能是数组（已处理）或分页对象（未处理）
      let dataArray: any[] = []
      
      if (Array.isArray(response)) {
        // 响应拦截器已经处理，直接是数组
        dataArray = response
        console.log('📊 DataSource Store: 收到处理后的数组响应')
      } else if (response && response.data && Array.isArray(response.data)) {
        // 响应是分页对象，提取data字段
        dataArray = response.data
        console.log('📊 DataSource Store: 收到分页响应，提取data数组')
      } else {
        console.warn('⚠️ DataSource Store: 响应数据格式异常', response)
        dataArray = []
      }
      
      dataSources.value = dataArray
      console.log('✅ DataSource Store: 数据源列表更新成功', dataArray.length, '个数据源')
      return response
    } catch (error) {
      console.error('❌ DataSource Store: 获取数据源列表失败', error)
      dataSources.value = []
      throw error
    } finally {
      isLoading.value = false
    }
  }

  // 根据ID获取数据源详情
  const fetchDataSourceById = async (id: string) => {
    isLoading.value = true
    try {
      console.log('📡 DataSource Store: 调用getDataSourceById API, ID:', id)
      const response = await dataSourceApi.getDataSourceById(id)
      console.log('📨 DataSource Store: getDataSourceById响应:', response)
      
      currentDataSource.value = response.data || response
      console.log('✅ DataSource Store: 数据源详情获取成功:', currentDataSource.value)
      return currentDataSource.value
    } catch (error) {
      console.error('❌ DataSource Store: 获取数据源详情失败:', error)
      
      // 如果API失败，尝试从当前数据源列表中查找
      console.log('🔄 DataSource Store: 尝试从缓存列表中查找数据源')
      if (Array.isArray(dataSources.value)) {
        const found = dataSources.value.find(ds => ds.id === id)
        if (found) {
          console.log('✅ DataSource Store: 从缓存中找到数据源:', found)
          currentDataSource.value = found
          return found
        }
      }
      
      throw error
    } finally {
      isLoading.value = false
    }
  }

  // 创建数据源
  const createDataSource = async (form: CreateDataSourceForm) => {
    isCreating.value = true
    try {
      console.log('📝 DataSource Store: 开始创建数据源', form)
      const response = await dataSourceApi.createDataSource(form)
      console.log('✅ DataSource Store: 创建数据源响应', response)
      
      // 检查响应数据结构
      const newDataSource = response.data || response
      if (newDataSource && newDataSource.id) {
        console.log('📊 DataSource Store: 新数据源数据', newDataSource)
        dataSources.value.push(newDataSource)
        console.log('📋 DataSource Store: 当前数据源列表', dataSources.value.length, '个数据源')
      } else {
        console.error('❌ DataSource Store: 无效的响应数据', response)
        console.warn('⚠️ DataSource Store: 创建响应数据无效，刷新列表')
        await fetchDataSources()
      }
      return response
    } catch (error) {
      console.error('❌ DataSource Store: 创建数据源失败', error)
      throw error
    } finally {
      isCreating.value = false
    }
  }

  // 更新数据源
  const updateDataSource = async (id: string, form: UpdateDataSourceForm) => {
    isUpdating.value = true
    try {
      const response = await dataSourceApi.updateDataSource(id, form)
      const updatedData = response.data || response
      
      if (updatedData) {
        const index = dataSources.value.findIndex(ds => ds.id === id)
        if (index !== -1) {
          dataSources.value[index] = updatedData
        }
        if (currentDataSource.value?.id === id) {
          currentDataSource.value = updatedData
        }
      } else {
        console.warn('⚠️ DataSource Store: 更新响应数据为空，刷新列表')
        await fetchDataSources()
      }
      return response
    } finally {
      isUpdating.value = false
    }
  }

  // 删除数据源
  const deleteDataSource = async (id: string) => {
    isDeleting.value = true
    try {
      await dataSourceApi.deleteDataSource(id)
      const index = dataSources.value.findIndex(ds => ds.id === id)
      if (index !== -1) {
        dataSources.value.splice(index, 1)
      }
      if (currentDataSource.value?.id === id) {
        currentDataSource.value = null
      }
    } finally {
      isDeleting.value = false
    }
  }

  // 测试数据源连接
  const testConnection = async (config: any) => {
    try {
      const response = await dataSourceApi.testConnection(config)
      return response
    } catch (error) {
      throw error
    }
  }

  // 清除当前数据源
  const clearCurrentDataSource = () => {
    currentDataSource.value = null
  }

  return {
    // 状态
    dataSources: readonly(dataSources),
    currentDataSource: readonly(currentDataSource),
    isLoading: readonly(isLoading),
    isCreating: readonly(isCreating),
    isUpdating: readonly(isUpdating),
    isDeleting: readonly(isDeleting),
    
    // 计算属性
    dataSourcesByType,
    totalCount,
    typeStatistics,
    
    // 方法
    fetchDataSources,
    fetchDataSourceById,
    getDataSource: fetchDataSourceById, // 添加别名方法
    createDataSource,
    updateDataSource,
    deleteDataSource,
    testConnection,
    clearCurrentDataSource
  }
})
