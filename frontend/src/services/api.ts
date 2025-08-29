import httpClient from "@/utils/http";
import type {
    UploadResponse,
    ParseResponse,
    StatusResponse,
    DecadePlansResponse,
    HistoryResponse,
    StatisticsResponse,
} from "@/types/api";

// API路径前缀
const API_PREFIX = import.meta.env.VITE_API_PREFIX || "/api/v1";

// 排产算法配置接口
export interface SchedulingAlgorithmConfig {
    merge_enabled: boolean;
    split_enabled: boolean;
    correction_enabled: boolean;
    parallel_enabled: boolean;
}

// 排产任务接口
export interface SchedulingTask {
    task_id: string;
    import_batch_id: string;
    task_name: string;
    status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED";
    current_stage: string;
    progress: number;
    total_records: number;
    processed_records: number;
    start_time?: string;
    end_time?: string;
    execution_duration?: number;
    error_message?: string;
    result_summary?: any;
    algorithm_config: SchedulingAlgorithmConfig;
}

// 工单接口
export interface WorkOrder {
    work_order_nr: string;
    work_order_type: "HJB" | "HWS"; // 后端实际返回的类型
    machine_type: "卷包机" | "喂丝机"; // 后端实际返回的类型
    machine_code: string;
    product_code: string;
    plan_quantity: number;
    safety_stock?: number;
    work_order_status: string; // 后端返回字符串格式，可能为PENDING等
    planned_start_time: string | null;
    planned_end_time: string | null;
    actual_start_time?: string | null;
    actual_end_time?: string | null;
    created_time?: string | null;
    updated_time?: string | null;
}

// 排产API响应接口
export interface SchedulingExecuteResponse {
    code: number;
    message: string;
    data: {
        task_id: string;
        import_batch_id: string;
        status: string;
        message: string;
    };
}

export interface SchedulingStatusResponse {
    code: number;
    message: string;
    data: SchedulingTask;
}

export interface WorkOrdersResponse {
    code: number;
    message: string;
    data: {
        work_orders: WorkOrder[];
        total_count: number;
        page: number;
        page_size: number;
        total_pages: number;
    };
}

// 可排产批次接口
export interface AvailableBatch {
    batch_id: string;
    file_name: string;
    total_records: number;
    valid_records: number;
    import_end_time: string;
    display_name: string;
    can_schedule: boolean;
}

export interface AvailableBatchesResponse {
    code: number;
    message: string;
    data: {
        available_batches: AvailableBatch[];
        total_count: number;
    };
}

export class DecadePlanAPI {
    /**
     * 上传旬计划文件
     * @param file Excel文件
     * @param onProgress 上传进度回调
     * @returns 上传结果
     */
    static async uploadFile(
        file: File,
        onProgress?: (progress: number) => void,
    ): Promise<UploadResponse> {
        const formData = new FormData();
        formData.append("file", file);

        const response = await httpClient.post<UploadResponse>(`${API_PREFIX}/plans/upload`, formData, {
            headers: {
                "Content-Type": "multipart/form-data",
            },
            onUploadProgress: (progressEvent) => {
                if (progressEvent.total && onProgress) {
                    const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    onProgress(progress);
                }
            },
        });

        return response.data;
    }

    /**
     * 解析旬计划文件
     * @param importBatchId 导入批次ID
     * @param forceReparse 是否强制重新解析
     * @returns 解析结果
     */
    static async parseFile(
        importBatchId: string,
        forceReparse: boolean = false,
    ): Promise<ParseResponse> {
        const response = await httpClient.post<ParseResponse>(
            `${API_PREFIX}/plans/${importBatchId}/parse`,
            {},
            {
                params: {
                    force_reparse: forceReparse,
                },
            },
        );

        return response.data;
    }

    /**
     * 查询解析状态
     * @param importBatchId 导入批次ID
     * @returns 状态信息
     */
    static async getParseStatus(importBatchId: string): Promise<StatusResponse> {
        const response = await httpClient.get<StatusResponse>(
            `${API_PREFIX}/plans/${importBatchId}/status`,
        );

        return response.data;
    }

    /**
     * 查询旬计划记录
     * @param importBatchId 导入批次ID
     * @returns 旬计划记录列表
     */
    static async getDecadePlans(importBatchId: string): Promise<DecadePlansResponse> {
        const response = await httpClient.get<DecadePlansResponse>(
            `${API_PREFIX}/plans/${importBatchId}/decade-plans`,
        );

        return response.data;
    }

    /**
     * 轮询解析状态直到完成
     * @param importBatchId 导入批次ID
     * @param onStatusUpdate 状态更新回调
     * @param maxAttempts 最大轮询次数
     * @param interval 轮询间隔(毫秒)
     * @returns 最终状态
     */
    static async pollParseStatus(
        importBatchId: string,
        onStatusUpdate?: (status: StatusResponse) => void,
        maxAttempts: number = 30,
        interval: number = 2000,
    ): Promise<StatusResponse> {
        for (let attempt = 0; attempt < maxAttempts; attempt++) {
            try {
                const statusResponse = await this.getParseStatus(importBatchId);

                if (onStatusUpdate) {
                    onStatusUpdate(statusResponse);
                }

                const status = statusResponse.data.import_status;

                // 如果解析完成或失败，返回结果
                if (status === "COMPLETED" || status === "FAILED") {
                    return statusResponse;
                }

                // 等待下次轮询
                if (attempt < maxAttempts - 1) {
                    await new Promise((resolve) => setTimeout(resolve, interval));
                }
            } catch (error) {
                console.error("轮询解析状态失败:", error);

                // 如果是最后一次尝试，抛出错误
                if (attempt === maxAttempts - 1) {
                    throw error;
                }

                // 否则等待重试
                await new Promise((resolve) => setTimeout(resolve, interval));
            }
        }

        throw new Error("解析状态轮询超时");
    }

    /**
     * 获取上传历史记录
     * @param page 页码，从1开始
     * @param pageSize 每页大小
     * @param status 过滤状态
     * @returns 历史记录列表
     */
    static async getUploadHistory(
        page: number = 1,
        pageSize: number = 20,
        status?: string,
    ): Promise<HistoryResponse> {
        const params: any = {
            page,
            page_size: pageSize,
        };

        if (status) {
            params.status = status;
        }

        const response = await httpClient.get<HistoryResponse>(`${API_PREFIX}/plans/history`, {
            params,
        });

        return response.data;
    }

    /**
     * 获取统计信息
     * @returns 统计数据
     */
    static async getStatistics(): Promise<StatisticsResponse> {
        const response = await httpClient.get<StatisticsResponse>(`${API_PREFIX}/plans/statistics`);

        return response.data;
    }

    /**
     * 获取可用于排产的批次列表
     * @returns 可排产批次列表
     */
    static async getAvailableBatchesForScheduling(): Promise<AvailableBatchesResponse> {
        const response = await httpClient.get<AvailableBatchesResponse>(
            `${API_PREFIX}/plans/available-for-scheduling`,
        );

        return response.data;
    }
}

export class SchedulingAPI {
    /**
     * 执行排产算法
     * @param importBatchId 导入批次ID
     * @param algorithmConfig 算法配置
     * @returns 排产任务信息
     */
    static async executeScheduling(
        importBatchId: string,
        algorithmConfig?: Partial<SchedulingAlgorithmConfig>,
    ): Promise<SchedulingExecuteResponse> {
        const response = await httpClient.post<SchedulingExecuteResponse>(
            `${API_PREFIX}/scheduling/execute`,
            {
                import_batch_id: importBatchId,
                algorithm_config: {
                    merge_enabled: true,
                    split_enabled: true,
                    correction_enabled: true,
                    parallel_enabled: true,
                    ...algorithmConfig,
                },
            },
        );

        return response.data;
    }

    /**
     * 查询排产任务状态
     * @param taskId 任务ID
     * @returns 任务状态信息
     */
    static async getTaskStatus(taskId: string): Promise<SchedulingStatusResponse> {
        const response = await httpClient.get<SchedulingStatusResponse>(
            `${API_PREFIX}/scheduling/tasks/${taskId}/status`,
        );

        return response.data;
    }

    /**
     * 轮询排产任务状态直到完成
     * @param taskId 任务ID
     * @param onStatusUpdate 状态更新回调
     * @param maxAttempts 最大轮询次数
     * @param interval 轮询间隔(毫秒)
     * @returns 最终状态
     */
    static async pollTaskStatus(
        taskId: string,
        onStatusUpdate?: (status: SchedulingStatusResponse) => void,
        maxAttempts: number = 60,
        interval: number = 3000,
    ): Promise<SchedulingStatusResponse> {
        for (let attempt = 0; attempt < maxAttempts; attempt++) {
            try {
                const statusResponse = await this.getTaskStatus(taskId);

                if (onStatusUpdate) {
                    onStatusUpdate(statusResponse);
                }

                const status = statusResponse.data.status;

                // 如果排产完成或失败，返回结果
                if (status === "COMPLETED" || status === "FAILED" || status === "CANCELLED") {
                    return statusResponse;
                }

                // 等待下次轮询
                if (attempt < maxAttempts - 1) {
                    await new Promise((resolve) => setTimeout(resolve, interval));
                }
            } catch (error) {
                console.error("轮询排产状态失败:", error);

                // 如果是最后一次尝试，抛出错误
                if (attempt === maxAttempts - 1) {
                    throw error;
                }

                // 否则等待重试
                await new Promise((resolve) => setTimeout(resolve, interval));
            }
        }

        throw new Error("排产状态轮询超时");
    }

    /**
     * 获取排产历史记录
     * @param params 查询参数
     * @returns 历史记录列表
     */
    static async getSchedulingHistory(params?: {
        page?: number;
        page_size?: number;
        status?: string;
        scheduling_status?: string;
        start_date?: string;
        end_date?: string;
        batch_id?: string;
        task_id?: string;
    }): Promise<ApiResponse<{
        records: any[];
        pagination: {
            page: number;
            page_size: number;
            total_count: number;
            total_pages: number;
            has_next: boolean;
            has_prev: boolean;
        };
    }>> {
        const queryParams = new URLSearchParams();

        if (params?.page) queryParams.append('page', params.page.toString());
        if (params?.page_size) queryParams.append('page_size', params.page_size.toString());
        if (params?.status) queryParams.append('status', params.status);
        if (params?.scheduling_status) queryParams.append('scheduling_status', params.scheduling_status);
        if (params?.batch_id) queryParams.append('batch_id', params.batch_id);

        const response = await httpClient.get<ApiResponse<{
            records: any[];
            pagination: any;
        }>>(
            `${API_PREFIX}/plans/history?${queryParams.toString()}`
        );

        return response.data;
    }
}

export class WorkOrderAPI {
    /**
     * 查询工单列表
     * @param params 查询参数
     * @returns 工单列表
     */
    static async getWorkOrders(params?: {
        task_id?: string;
        import_batch_id?: string;
        order_type?: "HJB" | "HWS"; // 与后端API一致
        status?: string;
        machine_code?: string;
        product_code?: string;
        page?: number;
        page_size?: number;
    }): Promise<WorkOrdersResponse> {
        const response = await httpClient.get<WorkOrdersResponse>(`${API_PREFIX}/work-orders`, {
            params,
        });

        return response.data;
    }
}

export class MESAPI {
    /**
     * 检查MES系统健康状态
     * @returns MES系统状态
     */
    static async checkHealth(): Promise<ApiResponse<any>> {
        const response = await httpClient.get<ApiResponse<any>>(`${API_PREFIX}/mes/health`);

        return response.data;
    }

    /**
     * 查询机台状态
     * @param machine_codes 机台代码列表
     * @returns 机台状态列表
     */
    static async getMachineStatus(machine_codes?: string[]): Promise<ApiResponse<any>> {
        const response = await httpClient.post<ApiResponse<any>>(`${API_PREFIX}/mes/machines/status`, {
            machine_codes,
        });

        return response.data;
    }

    /**
     * 推送工单到MES系统
     * @param work_orders 工单列表
     * @returns 推送结果
     */
    static async pushWorkOrders(work_orders: any[]): Promise<ApiResponse<any>> {
        const response = await httpClient.post<ApiResponse<any>>(`${API_PREFIX}/mes/work-orders/push`, {
            work_orders,
        });

        return response.data;
    }

    /**
     * 查询工单状态
     * @param work_order_nrs 工单号列表
     * @returns 工单状态列表
     */
    static async getWorkOrderStatus(work_order_nrs: string[]): Promise<ApiResponse<any>> {
        const response = await httpClient.post<ApiResponse<any>>(
            `${API_PREFIX}/mes/work-orders/status`,
            { work_order_nrs },
        );

        return response.data;
    }

    /**
     * 获取维护计划
     * @param machine_codes 机台代码列表
     * @returns 维护计划列表
     */
    static async getMaintenanceSchedule(machine_codes?: string[]): Promise<ApiResponse<any>> {
        const response = await httpClient.post<ApiResponse<any>>(
            `${API_PREFIX}/mes/maintenance/schedule`,
            { machine_codes },
        );

        return response.data;
    }

    /**
     * 获取最近的生产事件
     * @returns 生产事件列表
     */
    static async getRecentEvents(): Promise<ApiResponse<any>> {
        const response = await httpClient.get<ApiResponse<any>>(`${API_PREFIX}/mes/events/recent`);

        return response.data;
    }
}

// === 机台配置管理API ===

// 机台配置相关接口类型
export interface Machine {
    id: number;
    machine_code: string;
    machine_name: string;
    machine_type: 'PACKING' | 'FEEDING';
    equipment_type?: string;
    production_line?: string;
    status: 'ACTIVE' | 'INACTIVE' | 'MAINTENANCE';
    created_time: string;
    updated_time: string;
}

export interface MachineRelation {
    id: number;
    feeder_code: string;
    maker_code: string;
    relation_type: string;
    priority: number;
    created_time: string;
    updated_time: string;
}

export interface MachineSpeed {
    id: number;
    machine_code: string;
    article_nr: string;
    speed: number;  // 生产速度（箱/小时）
    efficiency_rate: number;  // 效率率（百分比）
    effective_from: string;
    effective_to?: string;
    status: string;
    created_time: string;
    updated_time: string;
}

export interface MaintenancePlan {
    id: number;
    plan_code: string;
    machine_code: string;
    maintenance_type: string;
    planned_start_time: string;
    planned_end_time: string;
    actual_start_time?: string;
    actual_end_time?: string;
    status: string;
    description?: string;
    created_time: string;
    updated_time: string;
}

export interface ShiftConfig {
    id: number;
    shift_name: string;
    shift_code: string;
    start_time: string;
    end_time: string;
    is_active: boolean;
    created_time: string;
    updated_time: string;
}

// 请求/响应类型
export interface MachineRequest {
    machine_code: string;
    machine_name: string;
    machine_type: 'PACKING' | 'FEEDING';
    equipment_type?: string;
    production_line?: string;
    status: 'ACTIVE' | 'INACTIVE' | 'MAINTENANCE';
}

export interface PaginatedResponse<T> {
    code: number;
    message: string;
    data: {
        items: T[];
        total: number;
        page: number;
        page_size: number;
    };
}

export interface ApiResponse<T> {
    code: number;
    message: string;
    data: T;
}

export class MachineConfigAPI {
    /**
     * 机台基础信息 CRUD
     */
    static async getMachines(params?: {
        machine_code?: string;
        machine_type?: string;
        status?: string;
        page?: number;
        page_size?: number;
    }): Promise<PaginatedResponse<Machine>> {
        const response = await httpClient.get<PaginatedResponse<Machine>>(`${API_PREFIX}/machines/machines`, {
            params,
        });
        return response.data;
    }

    static async createMachine(data: MachineRequest): Promise<ApiResponse<{ id: number }>> {
        const response = await httpClient.post<ApiResponse<{ id: number }>>(`${API_PREFIX}/machines/machines`, data);
        return response.data;
    }

    static async updateMachine(id: number, data: MachineRequest): Promise<ApiResponse<any>> {
        const response = await httpClient.put<ApiResponse<any>>(`${API_PREFIX}/machines/machines/${id}`, data);
        return response.data;
    }

    static async deleteMachine(id: number): Promise<ApiResponse<any>> {
        const response = await httpClient.delete<ApiResponse<any>>(`${API_PREFIX}/machines/machines/${id}`);
        return response.data;
    }

    /**
     * 机台关系 CRUD
     */
    static async getMachineRelations(params?: {
        feeder_code?: string;
        maker_code?: string;
        page?: number;
        page_size?: number;
    }): Promise<PaginatedResponse<MachineRelation>> {
        const response = await httpClient.get<PaginatedResponse<MachineRelation>>(`${API_PREFIX}/machines/machine-relations`, {
            params,
        });
        return response.data;
    }

    static async createMachineRelation(data: {
        feeder_code: string;
        maker_code: string;
        relation_type: string;
        priority: number;
    }): Promise<ApiResponse<{ id: number }>> {
        const response = await httpClient.post<ApiResponse<{ id: number }>>(`${API_PREFIX}/machines/machine-relations`, data);
        return response.data;
    }

    static async updateMachineRelation(id: number, data: {
        feeder_code: string;
        maker_code: string;
        relation_type: string;
        priority: number;
    }): Promise<ApiResponse<any>> {
        const response = await httpClient.put<ApiResponse<any>>(`${API_PREFIX}/machines/machine-relations/${id}`, data);
        return response.data;
    }

    static async deleteMachineRelation(id: number): Promise<ApiResponse<any>> {
        const response = await httpClient.delete<ApiResponse<any>>(`${API_PREFIX}/machines/machine-relations/${id}`);
        return response.data;
    }

    /**
     * 机台速度 CRUD
     */
    static async getMachineSpeeds(params?: {
        machine_code?: string;
        article_nr?: string;
        page?: number;
        page_size?: number;
    }): Promise<PaginatedResponse<MachineSpeed>> {
        const response = await httpClient.get<PaginatedResponse<MachineSpeed>>(`${API_PREFIX}/machines/machine-speeds`, {
            params,
        });
        return response.data;
    }

    static async createMachineSpeed(data: {
        machine_code: string;
        article_nr: string;
        speed: number;  // 生产速度（箱/小时）
        efficiency_rate: number;  // 效率率（百分比）
        effective_from?: string;
        status?: string;
    }): Promise<ApiResponse<{ id: number }>> {
        const response = await httpClient.post<ApiResponse<{ id: number }>>(`${API_PREFIX}/machines/machine-speeds`, data);
        return response.data;
    }

    static async updateMachineSpeed(id: number, data: {
        machine_code: string;
        article_nr: string;
        speed: number;  // 生产速度（箱/小时）
        efficiency_rate: number;  // 效率率（百分比）
        effective_from?: string;
        status?: string;
    }): Promise<ApiResponse<any>> {
        const response = await httpClient.put<ApiResponse<any>>(`${API_PREFIX}/machines/machine-speeds/${id}`, data);
        return response.data;
    }

    static async deleteMachineSpeed(id: number): Promise<ApiResponse<any>> {
        const response = await httpClient.delete<ApiResponse<any>>(`${API_PREFIX}/machines/machine-speeds/${id}`);
        return response.data;
    }

    /**
     * 维护计划 CRUD
     */
    static async getMaintenancePlans(params?: {
        machine_code?: string;
        status?: string;
        maintenance_type?: string;
        page?: number;
        page_size?: number;
    }): Promise<PaginatedResponse<MaintenancePlan>> {
        const response = await httpClient.get<PaginatedResponse<MaintenancePlan>>(`${API_PREFIX}/machines/maintenance-plans`, {
            params,
        });
        return response.data;
    }

    static async createMaintenancePlan(data: {
        plan_code: string;
        machine_code: string;
        maintenance_type: string;
        planned_start_time: string;
        planned_end_time: string;
        actual_start_time?: string;
        actual_end_time?: string;
        status: string;
        description?: string;
    }): Promise<ApiResponse<{ id: number }>> {
        const response = await httpClient.post<ApiResponse<{ id: number }>>(`${API_PREFIX}/machines/maintenance-plans`, data);
        return response.data;
    }

    static async updateMaintenancePlan(id: number, data: {
        plan_code: string;
        machine_code: string;
        maintenance_type: string;
        planned_start_time: string;
        planned_end_time: string;
        actual_start_time?: string;
        actual_end_time?: string;
        status: string;
        description?: string;
    }): Promise<ApiResponse<any>> {
        const response = await httpClient.put<ApiResponse<any>>(`${API_PREFIX}/machines/maintenance-plans/${id}`, data);
        return response.data;
    }

    static async deleteMaintenancePlan(id: number): Promise<ApiResponse<any>> {
        const response = await httpClient.delete<ApiResponse<any>>(`${API_PREFIX}/machines/maintenance-plans/${id}`);
        return response.data;
    }

    /**
     * 班次配置 CRUD
     */
    static async getShiftConfigs(params?: {
        shift_name?: string;
        is_active?: boolean;
        page?: number;
        page_size?: number;
    }): Promise<PaginatedResponse<ShiftConfig>> {
        const response = await httpClient.get<PaginatedResponse<ShiftConfig>>(`${API_PREFIX}/machines/shift-configs`, {
            params,
        });
        return response.data;
    }

    static async createShiftConfig(data: {
        shift_name: string;
        shift_code: string;
        start_time: string;
        end_time: string;
        is_active: boolean;
    }): Promise<ApiResponse<{ id: number }>> {
        const response = await httpClient.post<ApiResponse<{ id: number }>>(`${API_PREFIX}/machines/shift-configs`, data);
        return response.data;
    }

    static async updateShiftConfig(id: number, data: {
        shift_name: string;
        shift_code: string;
        start_time: string;
        end_time: string;
        is_active: boolean;
    }): Promise<ApiResponse<any>> {
        const response = await httpClient.put<ApiResponse<any>>(`${API_PREFIX}/machines/shift-configs/${id}`, data);
        return response.data;
    }

    static async deleteShiftConfig(id: number): Promise<ApiResponse<any>> {
        const response = await httpClient.delete<ApiResponse<any>>(`${API_PREFIX}/machines/shift-configs/${id}`);
        return response.data;
    }
}

export default DecadePlanAPI;
