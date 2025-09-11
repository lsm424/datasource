/**
 * 数据浏览系统 Node.js 客户端示例
 * 支持外部系统通过API接入数据浏览系统的所有功能
 */

const axios = require('axios');

class DataBrowserClient {
  constructor(baseURL = 'http://localhost:8000/api/v1') {
    this.baseURL = baseURL;
    this.token = null;
    
    // 创建axios实例
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    // 请求拦截器 - 自动添加认证头
    this.client.interceptors.request.use(
      (config) => {
        if (this.token) {
          config.headers.Authorization = `Bearer ${this.token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );
    
    // 响应拦截器 - 统一错误处理
    this.client.interceptors.response.use(
      (response) => response.data,
      (error) => {
        if (error.response) {
          throw new Error(`API错误 ${error.response.status}: ${error.response.data.detail || error.response.statusText}`);
        } else if (error.request) {
          throw new Error('网络错误：无法连接到服务器');
        } else {
          throw new Error(`请求错误: ${error.message}`);
        }
      }
    );
  }

  /**
   * 用户登录获取访问令牌
   */
  async login(username, password) {
    try {
      const response = await this.client.post('/auth/login', {
        username,
        password,
      });
      
      this.token = response.data.access_token;
      return response;
    } catch (error) {
      throw new Error(`登录失败: ${error.message}`);
    }
  }

  /**
   * 获取数据源列表
   */
  async getDatasources(options = {}) {
    const {
      page = 1,
      limit = 20,
      type = null,
      is_active = null,
      search = null,
    } = options;

    const params = { page, limit };
    if (type) params.type = type;
    if (is_active !== null) params.is_active = is_active;
    if (search) params.search = search;

    try {
      return await this.client.get('/datasources', { params });
    } catch (error) {
      throw new Error(`获取数据源列表失败: ${error.message}`);
    }
  }

  /**
   * 获取特定数据源详情
   */
  async getDatasourceDetail(datasourceId) {
    try {
      return await this.client.get(`/datasources/${datasourceId}`);
    } catch (error) {
      throw new Error(`获取数据源详情失败: ${error.message}`);
    }
  }

  /**
   * 浏览文件系统
   */
  async browseFilesystem(datasourceId, path = '/') {
    try {
      return await this.client.get(`/browse/filesystem/${datasourceId}/files`, {
        params: { path },
      });
    } catch (error) {
      throw new Error(`浏览文件系统失败: ${error.message}`);
    }
  }

  /**
   * 获取数据库表列表
   */
  async browseDatabaseTables(datasourceId, database = null) {
    const params = {};
    if (database) params.database = database;

    try {
      return await this.client.get(`/browse/database/${datasourceId}/tables`, {
        params,
      });
    } catch (error) {
      throw new Error(`获取数据库表列表失败: ${error.message}`);
    }
  }

  /**
   * 获取对象存储桶列表
   */
  async browseObjectStorageBuckets(datasourceId) {
    try {
      return await this.client.get(`/browse/object_storage/${datasourceId}/buckets`);
    } catch (error) {
      throw new Error(`获取对象存储桶列表失败: ${error.message}`);
    }
  }

  /**
   * 获取对象存储对象列表
   */
  async browseObjectStorageObjects(datasourceId, bucketName, options = {}) {
    const { prefix = '', delimiter = '/' } = options;

    try {
      return await this.client.get(
        `/browse/object_storage/${datasourceId}/buckets/${bucketName}/objects`,
        {
          params: { prefix, delimiter },
        }
      );
    } catch (error) {
      throw new Error(`获取对象存储对象列表失败: ${error.message}`);
    }
  }

  /**
   * 获取仪表盘统计数据
   */
  async getDashboardStats() {
    try {
      return await this.client.get('/dashboard/stats');
    } catch (error) {
      throw new Error(`获取统计数据失败: ${error.message}`);
    }
  }

  /**
   * 系统健康检查
   */
  async healthCheck() {
    try {
      return await this.client.get('/health');
    } catch (error) {
      throw new Error(`健康检查失败: ${error.message}`);
    }
  }
}

// 使用示例
async function example() {
  try {
    const client = new DataBrowserClient();

    // 登录系统
    console.log('🔐 正在登录...');
    const loginResult = await client.login('admin', 'admin'); // 替换为实际的用户名密码
    console.log(`✅ 登录成功！用户: ${loginResult.data.user.username}`);

    // 获取数据源列表
    console.log('\n📊 获取数据源列表...');
    const datasources = await client.getDatasources({ limit: 10 });
    console.log(`✅ 共找到 ${datasources.total} 个数据源`);

    for (const ds of datasources.data) {
      console.log(`   📁 ${ds.name} (${ds.type}) - ${ds.cname}`);

      // 获取数据源详情
      const detail = await client.getDatasourceDetail(ds.id);
      console.log(`      📝 描述: ${detail.data.desc}`);

      // 根据数据源类型进行不同的浏览操作
      if (ds.type === 'filesystem') {
        console.log(`      🗂️  浏览文件系统...`);
        try {
          const files = await client.browseFilesystem(ds.id);
          console.log(`      📄 根目录包含 ${files.data.length} 个文件/文件夹`);
        } catch (error) {
          console.log(`      ❌ 文件系统访问失败: ${error.message}`);
        }
      } else if (ds.type === 'database') {
        console.log(`      🗄️  浏览数据库表...`);
        try {
          const tables = await client.browseDatabaseTables(ds.id);
          console.log(`      📋 数据库包含 ${tables.data.length} 张表`);
        } catch (error) {
          console.log(`      ❌ 数据库连接失败: ${error.message}`);
        }
      } else if (ds.type === 'object_storage') {
        console.log(`      🪣 浏览对象存储...`);
        try {
          const buckets = await client.browseObjectStorageBuckets(ds.id);
          console.log(`      📦 对象存储包含 ${buckets.data.length} 个桶`);

          if (buckets.data.length > 0) {
            const firstBucket = buckets.data[0].name;
            const objects = await client.browseObjectStorageObjects(ds.id, firstBucket);
            console.log(`      📄 桶 '${firstBucket}' 包含 ${objects.data.length} 个对象`);
          }
        } catch (error) {
          console.log(`      ❌ 对象存储连接失败: ${error.message}`);
        }
      }
    }

    // 获取系统统计信息
    console.log('\n📈 获取系统统计信息...');
    const stats = await client.getDashboardStats();
    console.log(`✅ 数据源总数: ${stats.data.datasource_count}`);
    console.log(`✅ 总数据大小: ${stats.data.total_size} 字节`);
    console.log(`✅ 总文件数量: ${stats.data.total_files}`);

    // 系统健康检查
    console.log('\n🏥 系统健康检查...');
    const health = await client.healthCheck();
    console.log(`✅ 系统状态: ${health.data.status}`);
    console.log(
      `✅ 数据库连接: ${
        health.data.services.database.status === 'healthy' ? '正常' : '异常'
      }`
    );
  } catch (error) {
    console.error(`❌ 操作失败: ${error.message}`);
  }
}

// 导出客户端类
module.exports = DataBrowserClient;

// 如果直接运行此文件，则执行示例
if (require.main === module) {
  example();
}
