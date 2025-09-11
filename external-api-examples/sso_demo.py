#!/usr/bin/env python3
"""
数据浏览系统 SSO 集成演示脚本
展示各种SSO认证方式的实际使用方法
"""

import jwt
import requests
import json
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataBrowserSSODemo:
    """数据浏览系统SSO集成演示类"""
    
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.shared_secret = "your-shared-secret-key-change-this"  # 与数据浏览系统共享的密钥
        self.admin_token = None  # 管理员token，用于生成API Key
        
    def generate_shared_jwt_token(self, user_data: Dict[str, Any]) -> str:
        """生成与数据浏览系统兼容的JWT Token"""
        payload = {
            "sub": user_data["user_id"],
            "username": user_data["username"], 
            "role": user_data.get("role", "user"),
            "email": user_data.get("email"),
            "name": user_data.get("name"),
            "system": user_data.get("system", "external_demo"),
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        token = jwt.encode(payload, self.shared_secret, algorithm="HS256")
        logger.info(f"生成JWT Token用户: {user_data['username']}")
        return token
    
    def demo_jwt_shared_authentication(self):
        """演示JWT共享认证方式"""
        print("\n🔐 演示1: JWT Token共享认证")
        print("=" * 50)
        
        # 模拟外部系统用户数据
        user_data = {
            "user_id": "demo_user_001",
            "username": "demo_user",
            "email": "demo@example.com",
            "name": "演示用户",
            "role": "admin",
            "system": "external_demo_system"
        }
        
        # 生成JWT Token
        jwt_token = self.generate_shared_jwt_token(user_data)
        print(f"✅ 生成JWT Token: {jwt_token[:50]}...")
        
        # 使用JWT Token访问数据浏览系统API
        try:
            headers = {"Authorization": f"Bearer {jwt_token}"}
            response = requests.get(f"{self.base_url}/datasources", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 成功访问数据源API，找到 {data.get('total', 0)} 个数据源")
                return jwt_token
            else:
                print(f"❌ API访问失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            
        return None
    
    async def demo_external_token_validation(self):
        """演示外部Token验证方式"""
        print("\n🌐 演示2: 外部Token验证")
        print("=" * 50)
        
        # 模拟外部系统token
        external_token = "external_system_token_12345"
        system_name = "demo_system"
        
        try:
            # Token交换请求
            data = {
                "external_token": external_token,
                "system_name": system_name
            }
            
            response = requests.post(
                f"{self.base_url}/sso/token-exchange",
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                access_token = result["data"]["access_token"]
                user_info = result["data"]["user"]
                
                print(f"✅ Token交换成功")
                print(f"   用户: {user_info['username']} ({user_info['name']})")
                print(f"   角色: {user_info['role']}")
                print(f"   本地Token: {access_token[:50]}...")
                
                return access_token
            else:
                print(f"❌ Token交换失败: {response.status_code}")
                print(f"   注意: 这个演示需要配置外部系统验证端点")
                
        except Exception as e:
            print(f"❌ Token交换异常: {str(e)}")
            
        return None
    
    def demo_api_key_generation(self, admin_token: str):
        """演示API Key生成和使用"""
        print("\n🔑 演示3: API Key认证")
        print("=" * 50)
        
        try:
            # 生成API Key
            headers = {"Authorization": f"Bearer {admin_token}"}
            data = {
                "target_user_id": "demo_user_001",
                "system_name": "external_demo"
            }
            
            response = requests.post(
                f"{self.base_url}/sso/generate-api-key",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                api_key = result["data"]["api_key"]
                
                print(f"✅ API Key生成成功: {api_key[:50]}...")
                print(f"   有效期: {result['data']['expires_in_days']} 天")
                
                # 使用API Key访问API
                api_headers = {"Authorization": f"Bearer {api_key}"}
                api_response = requests.get(f"{self.base_url}/datasources", headers=api_headers)
                
                if api_response.status_code == 200:
                    data = api_response.json()
                    print(f"✅ 使用API Key成功访问API，找到 {data.get('total', 0)} 个数据源")
                else:
                    print(f"❌ API Key访问失败: {api_response.status_code}")
                    
                return api_key
            else:
                print(f"❌ API Key生成失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ API Key操作异常: {str(e)}")
            
        return None
    
    def demo_sso_user_info(self, token: str):
        """演示获取SSO用户信息"""
        print("\n👤 演示4: 获取SSO用户信息")
        print("=" * 50)
        
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(f"{self.base_url}/sso/me/mixed", headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                user_data = result["data"]
                sso_info = user_data.get("sso_info", {})
                
                print(f"✅ 用户信息获取成功:")
                print(f"   ID: {user_data['id']}")
                print(f"   用户名: {user_data['username']}")
                print(f"   姓名: {user_data['name']}")
                print(f"   邮箱: {user_data.get('email', 'N/A')}")
                print(f"   角色: {user_data['role']}")
                print(f"   SSO用户: {sso_info.get('is_sso_user', False)}")
                
                if sso_info.get('is_sso_user'):
                    print(f"   外部系统: {sso_info.get('sso_system', 'N/A')}")
                    print(f"   外部ID: {sso_info.get('external_id', 'N/A')}")
                    
            else:
                print(f"❌ 获取用户信息失败: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 获取用户信息异常: {str(e)}")
    
    def demo_data_browsing(self, token: str):
        """演示使用SSO token浏览数据"""
        print("\n📊 演示5: 使用SSO Token浏览数据")
        print("=" * 50)
        
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            # 获取数据源列表
            response = requests.get(f"{self.base_url}/datasources", headers=headers)
            
            if response.status_code == 200:
                datasources = response.json()
                print(f"✅ 数据源列表 (共{datasources.get('total', 0)}个):")
                
                for ds in datasources.get('data', [])[:3]:  # 显示前3个
                    print(f"   📁 {ds['name']} ({ds['type']}) - {ds['cname']}")
                    
                    # 根据数据源类型演示浏览
                    ds_id = ds['id']
                    if ds['type'] == 'filesystem':
                        self._demo_browse_filesystem(headers, ds_id, ds['name'])
                    elif ds['type'] == 'database':
                        self._demo_browse_database(headers, ds_id, ds['name'])
                    elif ds['type'] == 'object_storage':
                        self._demo_browse_object_storage(headers, ds_id, ds['name'])
            else:
                print(f"❌ 获取数据源失败: {response.status_code}")
                
            # 获取系统统计
            stats_response = requests.get(f"{self.base_url}/dashboard/stats", headers=headers)
            if stats_response.status_code == 200:
                stats = stats_response.json()['data']
                print(f"\n📈 系统统计:")
                print(f"   数据源总数: {stats.get('datasource_count', 0)}")
                print(f"   总文件数: {stats.get('total_files', 0)}")
                print(f"   总数据大小: {stats.get('total_size', 0)} 字节")
                
        except Exception as e:
            print(f"❌ 数据浏览异常: {str(e)}")
    
    def _demo_browse_filesystem(self, headers: Dict[str, str], ds_id: str, name: str):
        """演示文件系统浏览"""
        try:
            response = requests.get(
                f"{self.base_url}/browse/filesystem/{ds_id}/files?path=/",
                headers=headers
            )
            if response.status_code == 200:
                files = response.json()
                print(f"      🗂️  根目录包含 {len(files.get('data', []))} 个文件/文件夹")
        except:
            print(f"      ❌ {name} 文件系统访问失败")
    
    def _demo_browse_database(self, headers: Dict[str, str], ds_id: str, name: str):
        """演示数据库浏览"""
        try:
            response = requests.get(
                f"{self.base_url}/browse/database/{ds_id}/tables",
                headers=headers
            )
            if response.status_code == 200:
                tables = response.json()
                print(f"      🗄️  数据库包含 {len(tables.get('data', []))} 张表")
        except:
            print(f"      ❌ {name} 数据库访问失败")
    
    def _demo_browse_object_storage(self, headers: Dict[str, str], ds_id: str, name: str):
        """演示对象存储浏览"""
        try:
            response = requests.get(
                f"{self.base_url}/browse/object_storage/{ds_id}/buckets",
                headers=headers
            )
            if response.status_code == 200:
                buckets = response.json()
                print(f"      🪣 对象存储包含 {len(buckets.get('data', []))} 个桶")
        except:
            print(f"      ❌ {name} 对象存储访问失败")
    
    def demo_sso_integration_test(self):
        """演示SSO集成测试"""
        print("\n🧪 演示6: SSO集成测试")
        print("=" * 50)
        
        # 需要管理员权限
        if not self.admin_token:
            print("❌ 需要管理员Token才能运行集成测试")
            return
        
        # 生成测试token
        test_user = {
            "user_id": "test_user_999",
            "username": "test_user",
            "role": "user",
            "system": "test_system"
        }
        
        test_token = self.generate_shared_jwt_token(test_user)
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            data = {
                "test_token": test_token,
                "auth_type": "shared_jwt",
                "system_name": "test_system"
            }
            
            response = requests.post(
                f"{self.base_url}/sso/test-integration",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                test_results = result["data"]["test_results"]
                
                print(f"✅ SSO集成测试结果:")
                print(f"   整体状态: {result['data']['overall_status']}")
                
                if "token_validation" in test_results:
                    tv = test_results["token_validation"]
                    print(f"   Token验证: {'✅' if tv['success'] else '❌'}")
                    if tv['success']:
                        print(f"     用户ID: {tv['user_id']}")
                        print(f"     用户名: {tv['username']}")
                        print(f"     角色: {tv['role']}")
                
                if "user_management" in test_results:
                    um = test_results["user_management"]
                    print(f"   用户管理: {'✅' if um['success'] else '❌'}")
                    if um['success']:
                        print(f"     本地用户ID: {um['user_id']}")
                        print(f"     是否新建: {um['created_new']}")
                        
            else:
                print(f"❌ 集成测试失败: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 集成测试异常: {str(e)}")
    
    def setup_admin_token(self):
        """设置管理员token（用于演示）"""
        print("🔧 设置管理员Token...")
        
        # 尝试使用默认管理员账户登录
        login_data = {
            "username": "admin",
            "password": "admin"  # 请根据实际情况修改
        }
        
        try:
            response = requests.post(f"{self.base_url}/auth/login", json=login_data)
            
            if response.status_code == 200:
                result = response.json()
                self.admin_token = result["data"]["access_token"]
                print("✅ 管理员登录成功")
                return True
            else:
                print("❌ 管理员登录失败，部分功能将不可用")
                return False
                
        except Exception as e:
            print(f"❌ 管理员登录异常: {str(e)}")
            return False
    
    async def run_all_demos(self):
        """运行所有SSO演示"""
        print("🎯 数据浏览系统 SSO 集成演示")
        print("=" * 60)
        print("本演示展示如何在外部系统中集成数据浏览系统的单点登录功能")
        print()
        
        # 设置管理员token
        self.setup_admin_token()
        
        # 演示1: JWT共享认证
        jwt_token = self.demo_jwt_shared_authentication()
        
        if jwt_token:
            # 演示4: 获取用户信息
            self.demo_sso_user_info(jwt_token)
            
            # 演示5: 数据浏览
            self.demo_data_browsing(jwt_token)
        
        # 演示2: 外部Token验证（需要外部系统配置）
        await self.demo_external_token_validation()
        
        # 演示3: API Key认证
        if self.admin_token:
            api_key = self.demo_api_key_generation(self.admin_token)
            
            if api_key:
                self.demo_sso_user_info(api_key)
        
        # 演示6: 集成测试
        self.demo_sso_integration_test()
        
        print("\n🎉 所有SSO演示完成!")
        print("\n💡 提示:")
        print("   1. 确保数据浏览系统后端服务正在运行")
        print("   2. 检查SSO配置是否正确")
        print("   3. 生产环境请使用强密钥和HTTPS")


def main():
    """主函数"""
    demo = DataBrowserSSODemo()
    
    # 运行演示
    asyncio.run(demo.run_all_demos())


if __name__ == "__main__":
    main()
