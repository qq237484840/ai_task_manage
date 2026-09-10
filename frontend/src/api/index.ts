import type {
  AnalysisConfirmParams,
  AnalysisCreateParams,
  AnalysisGenerateResult,
  AnalysisItem,
  BatchKind,
  GateStatus,
  LinkReviewParams,
  LinkReviewResult,
  LinkSuggestionResult,
  ListResponse,
  ParseConfirmationPayload,
  Photo,
  PhotoListParams,
  School,
  Student,
  StudentPayload,
  TaskCreatePayload,
  TaskDetail,
  TaskGroup,
  TaskGroupListParams,
  TaskListParams,
  TaskStatus,
  TaskSummary,
  TaskUpdatePayload,
  UploadBatch,
  UploadPhotoResult,
} from "./types";
import { http } from "./http";

export type SubjectKind = "family" | "student";
export type AccountStatus = "active" | "disabled";

// ---- 认证：家长（family）----
export interface FamilyLoginResult {
  token: string;
  family_id?: string;
  display_name?: string;
}

export function familyLogin(login_name: string, password: string): Promise<FamilyLoginResult> {
  return http.post("/family/login", { login_name, password });
}

export function familyRegister(payload: {
  login_name: string;
  password: string;
  display_name?: string;
}): Promise<unknown> {
  return http.post("/family/register", payload);
}

export function familyLogout(): Promise<unknown> {
  return http.post("/family/logout");
}

// ---- 认证：学生子账号（student，ACR-001）----
export interface StudentLoginResult {
  token: string;
  subject_type: "student";
  student_id: string;
  student_name: string;
  expires_at: string;
}

export function studentLogin(login_name: string, password: string): Promise<StudentLoginResult> {
  return http.post("/student/login", { login_name, password });
}

export function studentLogout(): Promise<unknown> {
  return http.post("/student/logout");
}

export function studentMe(): Promise<Student> {
  return http.get("/student/me");
}

// ---- 学生子账号管理（家长专属，ACR-001）----
export interface AccountOpenPayload {
  login_name: string;
  password: string;
}
export interface AccountUpdatePayload {
  status?: AccountStatus;
  password?: string;
}
export interface AccountResult {
  student_id: string;
  login_name: string;
  status: AccountStatus;
  password_warning?: string | null;
}

export function openStudentAccount(
  student_id: string,
  payload: AccountOpenPayload
): Promise<AccountResult> {
  return http.post(`/students/${student_id}/account`, payload);
}

export function updateStudentAccount(
  student_id: string,
  payload: AccountUpdatePayload
): Promise<AccountResult> {
  return http.patch(`/students/${student_id}/account`, payload);
}

// ---- 学校字典（全局只读）----
let schoolsCache: School[] | null = null;
let schoolsByStageCache: Record<string, School[]> | null = null;

export async function fetchSchools(force = false): Promise<School[]> {
  if (schoolsCache && !force) return schoolsCache;
  const data = await http.get("/schools", { params: { page: 1, page_size: 100 } });
  const res = data as unknown as ListResponse<School>;
  schoolsCache = res.items;
  schoolsByStageCache = {};
  for (const s of schoolsCache) {
    (schoolsByStageCache[s.stage] = schoolsByStageCache[s.stage] || []).push(s);
  }
  return schoolsCache;
}

export function schoolsOfStage(stage: string): School[] {
  return schoolsByStageCache?.[stage] ?? [];
}

// ---- 学生档案 ----
export function listStudents(): Promise<Student[]> {
  return http.get("/students");
}

export function createStudent(payload: StudentPayload): Promise<Student> {
  return http.post("/students", payload);
}

export function updateStudent(student_id: string, payload: StudentPayload): Promise<Student> {
  return http.patch(`/students/${student_id}`, payload);
}

// ---- 任务（M001 v0.2.0 事实层按天；API-M001-007~011、018、021）----
export function listTasks(params: TaskListParams): Promise<ListResponse<TaskSummary>> {
  return http.get("/tasks", { params });
}

export function getTask(task_id: string): Promise<TaskDetail> {
  return http.get(`/tasks/${task_id}`);
}

/** 上传任务输入源（图片/粘贴文本；不填内容）→ 同日同类型重复上传为追加。 */
export function createTask(payload: TaskCreatePayload): Promise<TaskDetail> {
  return http.post("/tasks", payload);
}

export function updateTask(task_id: string, payload: TaskUpdatePayload): Promise<TaskDetail> {
  return http.patch(`/tasks/${task_id}`, payload);
}

export function changeTaskStatus(
  task_id: string,
  action: "publish" | "close" | "reopen"
): Promise<{ task_id: string; status: TaskStatus }> {
  return http.post(`/tasks/${task_id}/status`, { action });
}

/** 解析结果确认（显式 / 隐式；幂等，内容有差异时 409）。 */
export function confirmTaskParse(
  task_id: string,
  payload: ParseConfirmationPayload
): Promise<TaskDetail> {
  return http.post(`/tasks/${task_id}/parse-confirmation`, payload);
}

/** 手工改归属日（幂等；跨聚合连锁迁移；已消费 409）。 */
export function changeTaskBelongDate(task_id: string, belong_date: string): Promise<TaskDetail> {
  return http.post(`/tasks/${task_id}/belong-date`, { belong_date });
}

// ---- 聚合任务（API-M001-019/020；挂接与判定的统一载体）----
export function listTaskGroups(params: TaskGroupListParams): Promise<ListResponse<TaskGroup>> {
  const { window_type, ...rest } = params;
  return http.get("/task-groups", {
    params: { ...rest, ...(window_type ? { window_type } : {}) },
  });
}

export function getTaskGroup(group_id: string): Promise<TaskGroup> {
  return http.get(`/task-groups/${group_id}`);
}

// ---- M002 作业图片采集与归属（契约 v0.4.0：入口 kind / N:N 挂接 / 门控 / 完成分析）----
/** 上传批次；`kind` 由菜单入口决定（「任务」→ task_spec，「作业」→ homework）。 */
export function createUploadBatch(
  student_id?: string,
  kind: BatchKind = "homework"
): Promise<UploadBatch> {
  return http.post("/upload-batches", { ...(student_id ? { student_id } : {}), kind });
}

export function uploadPhoto(batch_id: string, file: Blob): Promise<UploadPhotoResult> {
  const form = new FormData();
  form.append("batch_id", batch_id);
  form.append("file", file, "page.jpg");
  return http.post("/photos", form);
}

/** 照片列表/待处理队列（API-M002-003；支持 kind / group_subject_id 过滤）。 */
export function listPhotos(params: PhotoListParams): Promise<ListResponse<Photo>> {
  return http.get("/photos", { params });
}

/**
 * 逐张挂接复核（API-M002-005 POST /photos/{id}/links）：
 * - accept：给 `link_id` 确认既有建议；给 `group_subject_id` 为手工挂接（兜底 B6）；
 * - reject：驳回（置 rejected_at）；
 * - relink：改挂（旧 `link_id` + 新 `group_subject_id`）。
 */
export function reviewPhotoLinks(
  photo_id: string,
  payload: LinkReviewParams
): Promise<LinkReviewResult> {
  return http.post(`/photos/${photo_id}/links`, payload);
}

/** 挂接建议查询 / 重试（API-M002-007；retry=true 触发幂等重试）。 */
export function getLinkSuggestions(
  photo_id: string,
  retry = false
): Promise<LinkSuggestionResult> {
  return http.get(`/photos/${photo_id}/link-suggestions`, { params: { retry } });
}

/** 窗口级门控状态（API-M002-008 GET /photo-gates）。 */
export function listPhotoGates(
  params: { student_id?: string; group_key?: string } = {}
): Promise<GateStatus[]> {
  return http.get("/photo-gates", { params });
}

/** 完成分析生成（API-M002-009；门控未达成 → 409 gate_not_satisfied）。 */
export function createCompletionAnalyses(
  payload: AnalysisCreateParams
): Promise<AnalysisGenerateResult> {
  return http.post("/completion-analyses", payload);
}

/** 完成分析确认（API-M002-010；可校正结论 → 回写判定单元并锁定照片）。 */
export function confirmCompletionAnalysis(
  analysis_id: string,
  payload: AnalysisConfirmParams = {}
): Promise<AnalysisItem> {
  return http.post(`/completion-analyses/${analysis_id}/confirmation`, payload);
}

/** 完成分析重跑（API-M002-011；仅 draft，run_no 递增生成新草稿）。 */
export function rerunCompletionAnalysis(analysis_id: string): Promise<AnalysisItem> {
  return http.post(`/completion-analyses/${analysis_id}/rerun`);
}

export function deletePhoto(photo_id: string): Promise<void> {
  return http.delete(`/photos/${photo_id}`);
}

/** 带鉴权取图（API-M002-004）：请求受控内容流为 Blob 并转 objectURL（<img> 无法携带 Bearer）。 */
export async function fetchPhotoBlob(
  photo_id: string,
  kind: "original" | "normalized" = "normalized"
): Promise<string> {
  const blob = (await http.get(`/photos/${photo_id}/content`, {
    params: { kind },
    responseType: "blob",
  })) as Blob;
  return URL.createObjectURL(blob);
}
