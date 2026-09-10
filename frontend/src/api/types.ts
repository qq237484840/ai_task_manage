// 与后端 /api/v1 REST 契约对齐的类型层（ADR-012：DTO 契约对齐）。
// 契约单一事实源：docs/modules/M001/MODULE_API.md（API-M001-001~012）。

export type Subject = "math" | "chinese" | "english";
export type Stage = "primary" | "junior" | "senior";
export type ItemType = "objective" | "subjective";
export type TaskStatus = "draft" | "published" | "in_progress" | "closed";

export interface School {
  school_id: string;
  name: string;
  stage: Stage;
}

export interface Student {
  student_id: string;
  name: string;
  relation?: string | null;
  grade_level?: string | null;
  school: School;
}

// ---- M001 v0.2.0 双层模型（ADR-013）：事实层按天 + 聚合层跨天 ----
export type SpecStatus = "placeholder" | "parsed" | "confirmed";
export type SourceKind = "text" | "image";
export type WindowType = "day" | "weekend" | "holiday";
export type Category = "school";

/** 输入源段落（上传任务时提交；图片 / 粘贴文本混排）。 */
export interface SourceInput {
  seq: number;
  kind: SourceKind;
  text_content?: string | null;
  photo_id?: string | null;
}

export interface Source {
  source_id: string;
  seq: number;
  kind: SourceKind;
  text_content?: string | null;
  photo_id?: string | null;
}

/** 内容项（AI 解析草稿 + 家长确认；不参与挂接与判定）。 */
export interface ContentItemInput {
  content_id?: string | null;
  subject: string;
  text: string;
}

export interface ContentItem extends ContentItemInput {
  content_id: string;
  seq: number;
}

export interface TaskSummary {
  task_id: string;
  student_id: string;
  student_name: string;
  category: string;
  /** 归属日 YYYY-MM-DD（4 点切日 + 时区计算并固化）。 */
  belong_date: string;
  /** 学期周次（AT_TERM_START 所在周周一起算）。 */
  week_index: number;
  window_type: WindowType;
  spec_status: SpecStatus;
  title: string;
  grade_level?: string | null;
  status: TaskStatus;
  deadline?: string | null;
  content_count?: number;
  source_count?: number;
  created_at: string;
  updated_at?: string;
}

export interface TaskDetail extends TaskSummary {
  contents: ContentItem[];
  sources: Source[];
}

/** POST /tasks：只上传输入源，不填内容（API-M001-007）。 */
export interface TaskCreatePayload {
  student_id: string;
  category?: Category;
  grade_level?: string | null;
  sources: SourceInput[];
}

/** PATCH /tasks/{id}：改标题/年级/截止 + 内容项整体替换（归属字段不可改）。 */
export interface TaskUpdatePayload {
  title?: string;
  grade_level?: string | null;
  deadline?: string | null;
  contents?: ContentItemInput[];
}

/** POST /tasks/{id}/parse-confirmation（API-M001-018）。 */
export interface ParseConfirmationPayload {
  confirmed?: boolean;
  contents?: ContentItemInput[] | null;
  implicit?: boolean;
  digest?: { subjects: string[]; content_texts: string[] } | null;
}

// ---- 聚合层（API-M001-019/020）----
export type ConclusionStatus = "pending" | "draft" | "confirmed";

export interface TaskGroupSubject {
  group_subject_id: string;
  subject: string;
  content_refs: string[];
  conclusion?: string | null;
  conclusion_status: ConclusionStatus;
}

export interface TaskGroup {
  group_id: string;
  student_id: string;
  category: string;
  group_key: string;
  display_name: string;
  window_type: WindowType;
  policy_version: string;
  subjects: TaskGroupSubject[];
  created_at: string;
}

export interface TaskGroupListParams {
  student_id?: string;
  week_index?: number;
  window_type?: WindowType | "";
  page?: number;
  page_size?: number;
}

export interface StudentPayload {
  name: string;
  relation?: string | null;
  grade_level?: string | null;
  school_id: string;
}

export interface ListResponse<T> {
  items: T[];
  total?: number;
  page?: number;
  page_size?: number;
}

// ---- M002 作业图片采集与归属（契约 v0.4.0：入口 kind / N:N 挂接 / 窗口门控 / 完成分析）----
// 依据 ADR-013 双层模型：挂接目标 = 聚合学科子任务（group_subject_id），不再有段级 assignment/suggestion。
export type PhotoStatus = "unassigned" | "suggested" | "assigned" | "rejected";
export type BatchKind = "task_spec" | "homework";
export type LinkSource = "ai" | "manual";
export type LinkAction = "accept" | "reject" | "relink";
export type AnalysisStatus = "draft" | "confirmed";
export type Conclusion = "完成" | "部分完成" | "未完成" | "无法判断";

export interface QualityCheckItem {
  id: string;
  passed: boolean;
  value?: number | null;
  threshold?: number | null;
  severity: "reject" | "warn";
}

export interface QualityReport {
  ruleset_version: string;
  passed: boolean;
  checks: QualityCheckItem[];
}

export interface ContentUrls {
  original: string;
  normalized: string;
}

/** 照片↔聚合学科子任务挂接（N:N；ADR-013）。 */
export interface PhotoLink {
  link_id: string;
  group_subject_id: string;
  /** 展示用学科名（解析失败可为空）。 */
  subject?: string | null;
  source: LinkSource;
  confidence?: number | null;
  confirmed_at?: string | null;
  rejected_at?: string | null;
  created_at: string;
}

export interface Photo {
  photo_id: string;
  batch_id: string;
  student_id: string;
  seq_no: number;
  kind: BatchKind;
  status: PhotoStatus;
  /** 窗口级归属任务（冗余；未挂接为 null）。 */
  task_id?: string | null;
  links: PhotoLink[];
  quality: QualityReport;
  content_urls: ContentUrls;
  created_at: string;
}

export interface UploadBatch {
  batch_id: string;
  family_id: string;
  student_id: string;
  kind: BatchKind;
  created_by_type: "family" | "student";
  created_by_id: string;
  created_at: string;
}

export interface UploadPhotoResult {
  photo_id: string;
  batch: { batch_id: string; student_id: string; kind: BatchKind };
  seq_no: number;
  kind: BatchKind;
  status: PhotoStatus;
  quality: QualityReport;
  content_urls: ContentUrls;
}

export interface PhotoListParams {
  student_id?: string;
  status?: PhotoStatus | "";
  batch_id?: string;
  kind?: BatchKind | "";
  /** 过滤窗口级归属任务。 */
  task_id?: string;
  /** 过滤已挂接该聚合子任务的照片。 */
  group_subject_id?: string;
  page?: number;
  page_size?: number;
}

/** POST /photos/{id}/links（API-M002-005 逐张复核：accept|reject|relink）。 */
export interface LinkReviewParams {
  action: LinkAction;
  /** 定位既有挂接（accept / reject / relink 旧链）。 */
  link_id?: string;
  /** 复核目标聚合学科子任务（accept 手工兜底 / relink 新目标）。 */
  group_subject_id?: string;
}

/** 窗口级门控状态（API-M002-008）。 */
export interface GateStatus {
  group_key: string;
  window_type: string;
  total_photos: number;
  pending_photos: number;
  satisfied: boolean;
}

export interface LinkReviewResult {
  photo_id: string;
  status: PhotoStatus;
  task_id?: string | null;
  links: PhotoLink[];
  gate?: GateStatus | null;
}

/** GET /photos/{id}/link-suggestions（API-M002-007 挂接建议查询/重试）。 */
export interface LinkSuggestionItem {
  link_id: string;
  group_subject_id: string;
  subject?: string | null;
  confidence?: number | null;
  source: LinkSource;
  suggested_at: string;
}

export interface LinkSuggestionResult {
  photo_id: string;
  status: PhotoStatus;
  suggestions: LinkSuggestionItem[];
}

/** 完成分析项（API-M002-009~011；结论 + 依据照片 + 置信度）。 */
export interface AnalysisItem {
  analysis_id: string;
  group_subject_id: string;
  subject?: string | null;
  conclusion: Conclusion;
  evidence_photo_ids: string[];
  confidence?: number | null;
  status: AnalysisStatus;
  model?: string | null;
  prompt_version?: string | null;
  run_no: number;
  confirmed_by?: string | null;
  confirmed_at?: string | null;
  created_at: string;
}

/** POST /completion-analyses（API-M002-009；窗口级生成）。 */
export interface AnalysisCreateParams {
  student_id?: string | null;
  group_key: string;
}

export interface AnalysisGenerateResult {
  group_key: string;
  items: AnalysisItem[];
}

/** POST /completion-analyses/{id}/confirmation（API-M002-010；可校正结论）。 */
export interface AnalysisConfirmParams {
  conclusion?: Conclusion | null;
}

export interface TaskListParams {
  page?: number;
  page_size?: number;
  status?: TaskStatus | "";
  student_id?: string;
  belong_date?: string;
  week_index?: number;
}
