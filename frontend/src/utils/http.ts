import axios, { type AxiosInstance, type AxiosResponse, type AxiosError } from "axios";
import { ElMessage } from "element-plus";
import { handleError } from "./error-handler";
import type { BaseResponse } from "@/types/api";

// 创建axios实例
const httpClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// 请求拦截器
httpClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token等
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    return config;
  },
  (error) => {
    console.error("请求拦截器错误:", error);
    return Promise.reject(error);
  },
);

// 响应拦截器
httpClient.interceptors.response.use(
  (response: AxiosResponse<BaseResponse>) => {
    const { data } = response;

    // 检查业务状态码
    if (data.code === 200) {
      return response;
    } else {
      // 业务错误
      ElMessage.error(data.message || "请求失败");
      return Promise.reject(new Error(data.message || "请求失败"));
    }
  },
  (error: AxiosError) => {
    // 对于400错误（业务逻辑错误），让上层组件自行处理，避免重复显示
    if (error.response?.status === 400) {
      return Promise.reject(error);
    }

    // 构建更清晰的错误消息
    let errorMessage = '未知错误';
    if (error.response?.data?.message) {
      errorMessage = error.response.data.message;
    } else if (error.response?.data?.detail) {
      errorMessage = error.response.data.detail;
    } else if (error.message) {
      errorMessage = error.message;
    } else if (error.response?.status) {
      errorMessage = `HTTP ${error.response.status} 错误`;
    }

    // 只显示清晰的错误信息，避免 [object Object]
    ElMessage.error(`HTTP请求失败: ${errorMessage}`);
    
    console.error('HTTP请求错误详情:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      data: error.response?.data,
      message: error.message
    });
    
    return Promise.reject(error);
  },
);

export default httpClient;
