/**
 * 数据浏览系统 Java 客户端示例
 * 支持外部系统通过API接入数据浏览系统的所有功能
 * 
 * 依赖：
 * - OkHttp3 (网络请求)
 * - Jackson (JSON序列化)
 * 
 * Maven依赖:
 * <dependency>
 *     <groupId>com.squareup.okhttp3</groupId>
 *     <artifactId>okhttp</artifactId>
 *     <version>4.11.0</version>
 * </dependency>
 * <dependency>
 *     <groupId>com.fasterxml.jackson.core</groupId>
 *     <artifactId>jackson-databind</artifactId>
 *     <version>2.15.2</version>
 * </dependency>
 */

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

public class DataBrowserClient {
    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");
    
    private final OkHttpClient client;
    private final ObjectMapper objectMapper;
    private final String baseUrl;
    private String token;
    
    public DataBrowserClient() {
        this("http://localhost:8000/api/v1");
    }
    
    public DataBrowserClient(String baseUrl) {
        this.baseUrl = baseUrl;
        this.objectMapper = new ObjectMapper();
        
        // 配置HTTP客户端
        this.client = new OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build();
    }
    
    /**
     * 用户登录获取访问令牌
     */
    public ApiResponse login(String username, String password) throws IOException {
        Map<String, String> loginData = new HashMap<>();
        loginData.put("username", username);
        loginData.put("password", password);
        
        String json = objectMapper.writeValueAsString(loginData);
        RequestBody body = RequestBody.create(json, JSON);
        
        Request request = new Request.Builder()
            .url(baseUrl + "/auth/login")
            .post(body)
            .build();
        
        try (Response response = client.newCall(request).execute()) {
            String responseBody = response.body().string();
            
            if (response.isSuccessful()) {
                JsonNode jsonNode = objectMapper.readTree(responseBody);
                this.token = jsonNode.get("data").get("access_token").asText();
                return new ApiResponse(true, responseBody, response.code());
            } else {
                throw new RuntimeException("登录失败: " + response.code() + " - " + responseBody);
            }
        }
    }
    
    /**
     * 获取数据源列表
     */
    public ApiResponse getDatasources(int page, int limit, String type, Boolean isActive, String search) throws IOException {
        HttpUrl.Builder urlBuilder = HttpUrl.parse(baseUrl + "/datasources").newBuilder()
            .addQueryParameter("page", String.valueOf(page))
            .addQueryParameter("limit", String.valueOf(limit));
        
        if (type != null) urlBuilder.addQueryParameter("type", type);
        if (isActive != null) urlBuilder.addQueryParameter("is_active", isActive.toString());
        if (search != null) urlBuilder.addQueryParameter("search", search);
        
        Request request = createAuthenticatedRequest()
            .url(urlBuilder.build())
            .get()
            .build();
        
        return executeRequest(request);
    }
    
    /**
     * 获取特定数据源详情
     */
    public ApiResponse getDatasourceDetail(String datasourceId) throws IOException {
        Request request = createAuthenticatedRequest()
            .url(baseUrl + "/datasources/" + datasourceId)
            .get()
            .build();
        
        return executeRequest(request);
    }
    
    /**
     * 浏览文件系统
     */
    public ApiResponse browseFilesystem(String datasourceId, String path) throws IOException {
        HttpUrl url = HttpUrl.parse(baseUrl + "/browse/filesystem/" + datasourceId + "/files").newBuilder()
            .addQueryParameter("path", path != null ? path : "/")
            .build();
        
        Request request = createAuthenticatedRequest()
            .url(url)
            .get()
            .build();
        
        return executeRequest(request);
    }
    
    /**
     * 获取数据库表列表
     */
    public ApiResponse browseDatabaseTables(String datasourceId, String database) throws IOException {
        HttpUrl.Builder urlBuilder = HttpUrl.parse(baseUrl + "/browse/database/" + datasourceId + "/tables").newBuilder();
        
        if (database != null) {
            urlBuilder.addQueryParameter("database", database);
        }
        
        Request request = createAuthenticatedRequest()
            .url(urlBuilder.build())
            .get()
            .build();
        
        return executeRequest(request);
    }
    
    /**
     * 获取对象存储桶列表
     */
    public ApiResponse browseObjectStorageBuckets(String datasourceId) throws IOException {
        Request request = createAuthenticatedRequest()
            .url(baseUrl + "/browse/object_storage/" + datasourceId + "/buckets")
            .get()
            .build();
        
        return executeRequest(request);
    }
    
    /**
     * 获取对象存储对象列表
     */
    public ApiResponse browseObjectStorageObjects(String datasourceId, String bucketName, String prefix, String delimiter) throws IOException {
        HttpUrl.Builder urlBuilder = HttpUrl.parse(baseUrl + "/browse/object_storage/" + datasourceId + "/buckets/" + bucketName + "/objects").newBuilder();
        
        if (prefix != null) urlBuilder.addQueryParameter("prefix", prefix);
        if (delimiter != null) urlBuilder.addQueryParameter("delimiter", delimiter);
        
        Request request = createAuthenticatedRequest()
            .url(urlBuilder.build())
            .get()
            .build();
        
        return executeRequest(request);
    }
    
    /**
     * 获取仪表盘统计数据
     */
    public ApiResponse getDashboardStats() throws IOException {
        Request request = createAuthenticatedRequest()
            .url(baseUrl + "/dashboard/stats")
            .get()
            .build();
        
        return executeRequest(request);
    }
    
    /**
     * 系统健康检查
     */
    public ApiResponse healthCheck() throws IOException {
        Request request = createAuthenticatedRequest()
            .url(baseUrl + "/health")
            .get()
            .build();
        
        return executeRequest(request);
    }
    
    /**
     * 创建带认证头的请求构建器
     */
    private Request.Builder createAuthenticatedRequest() {
        Request.Builder builder = new Request.Builder();
        if (token != null) {
            builder.header("Authorization", "Bearer " + token);
        }
        builder.header("Content-Type", "application/json");
        return builder;
    }
    
    /**
     * 执行HTTP请求
     */
    private ApiResponse executeRequest(Request request) throws IOException {
        try (Response response = client.newCall(request).execute()) {
            String responseBody = response.body().string();
            return new ApiResponse(response.isSuccessful(), responseBody, response.code());
        }
    }
    
    /**
     * API响应包装类
     */
    public static class ApiResponse {
        private final boolean success;
        private final String body;
        private final int code;
        
        public ApiResponse(boolean success, String body, int code) {
            this.success = success;
            this.body = body;
            this.code = code;
        }
        
        public boolean isSuccess() { return success; }
        public String getBody() { return body; }
        public int getCode() { return code; }
        
        public JsonNode getJsonData() throws IOException {
            ObjectMapper mapper = new ObjectMapper();
            return mapper.readTree(body);
        }
    }
    
    /**
     * 使用示例
     */
    public static void main(String[] args) {
        try {
            DataBrowserClient client = new DataBrowserClient();
            
            // 登录系统
            System.out.println("🔐 正在登录...");
            ApiResponse loginResult = client.login("admin", "admin"); // 替换为实际的用户名密码
            
            if (loginResult.isSuccess()) {
                JsonNode loginData = loginResult.getJsonData();
                String username = loginData.get("data").get("user").get("username").asText();
                System.out.println("✅ 登录成功！用户: " + username);
                
                // 获取数据源列表
                System.out.println("\n📊 获取数据源列表...");
                ApiResponse datasources = client.getDatasources(1, 10, null, null, null);
                
                if (datasources.isSuccess()) {
                    JsonNode dsData = datasources.getJsonData();
                    int total = dsData.get("total").asInt();
                    System.out.println("✅ 共找到 " + total + " 个数据源");
                    
                    JsonNode dataList = dsData.get("data");
                    for (JsonNode ds : dataList) {
                        String name = ds.get("name").asText();
                        String type = ds.get("type").asText();
                        String cname = ds.get("cname").asText();
                        String id = ds.get("id").asText();
                        
                        System.out.println("   📁 " + name + " (" + type + ") - " + cname);
                        
                        // 获取数据源详情
                        ApiResponse detail = client.getDatasourceDetail(id);
                        if (detail.isSuccess()) {
                            JsonNode detailData = detail.getJsonData();
                            String desc = detailData.get("data").get("desc").asText();
                            System.out.println("      📝 描述: " + desc);
                            
                            // 根据数据源类型进行不同的浏览操作
                            switch (type) {
                                case "filesystem":
                                    System.out.println("      🗂️  浏览文件系统...");
                                    try {
                                        ApiResponse files = client.browseFilesystem(id, "/");
                                        if (files.isSuccess()) {
                                            JsonNode filesData = files.getJsonData();
                                            int fileCount = filesData.get("data").size();
                                            System.out.println("      📄 根目录包含 " + fileCount + " 个文件/文件夹");
                                        }
                                    } catch (Exception e) {
                                        System.out.println("      ❌ 文件系统访问失败: " + e.getMessage());
                                    }
                                    break;
                                    
                                case "database":
                                    System.out.println("      🗄️  浏览数据库表...");
                                    try {
                                        ApiResponse tables = client.browseDatabaseTables(id, null);
                                        if (tables.isSuccess()) {
                                            JsonNode tablesData = tables.getJsonData();
                                            int tableCount = tablesData.get("data").size();
                                            System.out.println("      📋 数据库包含 " + tableCount + " 张表");
                                        }
                                    } catch (Exception e) {
                                        System.out.println("      ❌ 数据库连接失败: " + e.getMessage());
                                    }
                                    break;
                                    
                                case "object_storage":
                                    System.out.println("      🪣 浏览对象存储...");
                                    try {
                                        ApiResponse buckets = client.browseObjectStorageBuckets(id);
                                        if (buckets.isSuccess()) {
                                            JsonNode bucketsData = buckets.getJsonData();
                                            int bucketCount = bucketsData.get("data").size();
                                            System.out.println("      📦 对象存储包含 " + bucketCount + " 个桶");
                                            
                                            if (bucketCount > 0) {
                                                String firstBucket = bucketsData.get("data").get(0).get("name").asText();
                                                ApiResponse objects = client.browseObjectStorageObjects(id, firstBucket, "", "/");
                                                if (objects.isSuccess()) {
                                                    JsonNode objectsData = objects.getJsonData();
                                                    int objectCount = objectsData.get("data").size();
                                                    System.out.println("      📄 桶 '" + firstBucket + "' 包含 " + objectCount + " 个对象");
                                                }
                                            }
                                        }
                                    } catch (Exception e) {
                                        System.out.println("      ❌ 对象存储连接失败: " + e.getMessage());
                                    }
                                    break;
                            }
                        }
                    }
                }
                
                // 获取系统统计信息
                System.out.println("\n📈 获取系统统计信息...");
                ApiResponse stats = client.getDashboardStats();
                if (stats.isSuccess()) {
                    JsonNode statsData = stats.getJsonData();
                    JsonNode data = statsData.get("data");
                    System.out.println("✅ 数据源总数: " + data.get("datasource_count").asInt());
                    System.out.println("✅ 总数据大小: " + data.get("total_size").asLong() + " 字节");
                    System.out.println("✅ 总文件数量: " + data.get("total_files").asInt());
                }
                
                // 系统健康检查
                System.out.println("\n🏥 系统健康检查...");
                ApiResponse health = client.healthCheck();
                if (health.isSuccess()) {
                    JsonNode healthData = health.getJsonData();
                    String status = healthData.get("data").get("status").asText();
                    String dbStatus = healthData.get("data").get("services").get("database").get("status").asText();
                    System.out.println("✅ 系统状态: " + status);
                    System.out.println("✅ 数据库连接: " + ("healthy".equals(dbStatus) ? "正常" : "异常"));
                }
                
            } else {
                System.out.println("❌ 登录失败");
            }
            
        } catch (Exception e) {
            System.out.println("❌ 操作失败: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
