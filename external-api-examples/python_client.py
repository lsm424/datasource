"""
数据浏览系统 Python 客户端示例
支持外部系统通过API接入数据浏览系统的所有功能
"""
import requests
import json
from typing import Dict, List, Optional, Any

class DataBrowserClient:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.token = None
        self.headers = {
            'Content-Type': 'application/json'
        }
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """用户登录获取访问令牌"""
        url = f"{self.base_url}/auth/login"
        data = {
            "username": username,
            "password": password
        }
        
        response = requests.post(url, json=data, headers=self.headers)
        
        if response.status_code == 200:
            result = response.json()
            self.token = result['data']['access_token']
            # 更新请求头，包含认证信息
            self.headers['Authorization'] = f"Bearer {self.token}"
            return result
        else:
            raise Exception(f"登录失败: {response.status_code} - {response.text}")
    
    def get_datasources(self, page: int = 1, limit: int = 20, 
                       ds_type: str = None, is_active: bool = None,
                       search: str = None) -> Dict[str, Any]:
        """获取数据源列表"""
        url = f"{self.base_url}/datasources"
        params = {"page": page, "limit": limit}
        
        if ds_type:
            params["type"] = ds_type
        if is_active is not None:
            params["is_active"] = is_active
        if search:
            params["search"] = search
        
        response = requests.get(url, params=params, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"获取数据源列表失败: {response.status_code} - {response.text}")
    
    def get_datasource_detail(self, datasource_id: str) -> Dict[str, Any]:
        """获取特定数据源详情"""
        url = f"{self.base_url}/datasources/{datasource_id}"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"获取数据源详情失败: {response.status_code} - {response.text}")
    
    def browse_filesystem(self, datasource_id: str, path: str = "/") -> Dict[str, Any]:
        """浏览文件系统"""
        url = f"{self.base_url}/browse/filesystem/{datasource_id}/files"
        params = {"path": path}
        
        response = requests.get(url, params=params, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"浏览文件系统失败: {response.status_code} - {response.text}")
    
    def browse_database_tables(self, datasource_id: str, database: str = None) -> Dict[str, Any]:
        """获取数据库表列表"""
        url = f"{self.base_url}/browse/database/{datasource_id}/tables"
        params = {}
        
        if database:
            params["database"] = database
        
        response = requests.get(url, params=params, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"获取数据库表列表失败: {response.status_code} - {response.text}")
    
    def browse_object_storage_buckets(self, datasource_id: str) -> Dict[str, Any]:
        """获取对象存储桶列表"""
        url = f"{self.base_url}/browse/object_storage/{datasource_id}/buckets"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"获取对象存储桶列表失败: {response.status_code} - {response.text}")
    
    def browse_object_storage_objects(self, datasource_id: str, bucket_name: str, 
                                    prefix: str = "", delimiter: str = "/") -> Dict[str, Any]:
        """获取对象存储对象列表"""
        url = f"{self.base_url}/browse/object_storage/{datasource_id}/buckets/{bucket_name}/objects"
        params = {"prefix": prefix, "delimiter": delimiter}
        
        response = requests.get(url, params=params, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"获取对象存储对象列表失败: {response.status_code} - {response.text}")
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """获取仪表盘统计数据"""
        url = f"{self.base_url}/dashboard/stats"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"获取统计数据失败: {response.status_code} - {response.text}")
    
    def health_check(self) -> Dict[str, Any]:
        """系统健康检查"""
        url = f"{self.base_url}/health"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"健康检查失败: {response.status_code} - {response.text}")


# 使用示例
if __name__ == "__main__":
    try:
        # 创建客户端实例
        client = DataBrowserClient()
        
        # 登录系统
        print("🔐 正在登录...")
        login_result = client.login("admin", "admin")  # 替换为实际的用户名密码
        print(f"✅ 登录成功！用户: {login_result['data']['user']['username']}")
        
        # 获取数据源列表
        print("\n📊 获取数据源列表...")
        datasources = client.get_datasources(limit=10)
        print(f"✅ 共找到 {datasources['total']} 个数据源")
        
        for ds in datasources['data']:
            print(f"   📁 {ds['name']} ({ds['type']}) - {ds['cname']}")
            
            # 获取数据源详情
            detail = client.get_datasource_detail(ds['id'])
            print(f"      📝 描述: {detail['data']['desc']}")
            
            # 根据数据源类型进行不同的浏览操作
            if ds['type'] == 'filesystem':
                print(f"      🗂️  浏览文件系统...")
                files = client.browse_filesystem(ds['id'])
                print(f"      📄 根目录包含 {len(files['data'])} 个文件/文件夹")
                
            elif ds['type'] == 'database':
                print(f"      🗄️  浏览数据库表...")
                try:
                    tables = client.browse_database_tables(ds['id'])
                    print(f"      📋 数据库包含 {len(tables['data'])} 张表")
                except Exception as e:
                    print(f"      ❌ 数据库连接失败: {str(e)}")
                    
            elif ds['type'] == 'object_storage':
                print(f"      🪣 浏览对象存储...")
                try:
                    buckets = client.browse_object_storage_buckets(ds['id'])
                    print(f"      📦 对象存储包含 {len(buckets['data'])} 个桶")
                    
                    if buckets['data']:
                        # 浏览第一个桶的内容
                        first_bucket = buckets['data'][0]['name']
                        objects = client.browse_object_storage_objects(ds['id'], first_bucket)
                        print(f"      📄 桶 '{first_bucket}' 包含 {len(objects['data'])} 个对象")
                        
                except Exception as e:
                    print(f"      ❌ 对象存储连接失败: {str(e)}")
        
        # 获取系统统计信息
        print(f"\n📈 获取系统统计信息...")
        stats = client.get_dashboard_stats()
        print(f"✅ 数据源总数: {stats['data']['datasource_count']}")
        print(f"✅ 总数据大小: {stats['data']['total_size']} 字节")
        print(f"✅ 总文件数量: {stats['data']['total_files']}")
        
        # 系统健康检查
        print(f"\n🏥 系统健康检查...")
        health = client.health_check()
        print(f"✅ 系统状态: {health['data']['status']}")
        print(f"✅ 数据库连接: {'正常' if health['data']['services']['database']['status'] == 'healthy' else '异常'}")
        
    except Exception as e:
        print(f"❌ 操作失败: {str(e)}")
