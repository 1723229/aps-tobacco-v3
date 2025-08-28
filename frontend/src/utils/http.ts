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

    // 其他错误使用统一错误处理器
    handleError(error, "HTTP请求");
    return Promise.reject(error);
  },
);

export default httpClient;
