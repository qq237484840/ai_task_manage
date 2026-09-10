import type { Stage, Subject } from "@/api/types";

const SUBJECTS: Record<Subject, string> = {
  math: "数学",
  chinese: "语文",
  english: "英语",
};

const STAGES: Record<Stage, string> = {
  primary: "小学",
  junior: "初中",
  senior: "高中",
};

export const STATUS_TEXT: Record<string, string> = {
  draft: "草稿",
  published: "已发布",
  in_progress: "进行中",
  closed: "已关闭",
};

// M001 v0.2.0：输入源解析状态（ADR-013 链路 T）
export const SPEC_STATUS_TEXT: Record<string, string> = {
  placeholder: "待解析",
  parsed: "已解析",
  confirmed: "已确认",
};

// 归属窗口类型（4 点切日 / 周末合并 / 假期）
export const WINDOW_TYPE_TEXT: Record<string, string> = {
  day: "当日",
  weekend: "周末",
  holiday: "假期",
};

export function weekText(weekIndex?: number | null): string {
  return weekIndex ? `第 ${weekIndex} 周` : "-";
}

export function subjectText(v: Subject | string): string {
  return SUBJECTS[v as Subject] ?? v;
}

export function stageText(v: Stage | string): string {
  return STAGES[v as Stage] ?? v;
}

export function itemTypeText(v: string): string {
  return v === "objective" ? "客观题" : v === "subjective" ? "主观题" : v;
}

// M002 照片状态（API-M002）
export const PHOTO_STATUS_TEXT: Record<string, string> = {
  unassigned: "待处理",
  suggested: "建议待采纳",
  assigned: "已归属",
  rejected: "已驳回",
};

export function qualitySeverityText(sev: string): string {
  return sev === "reject" ? "不合格" : sev === "warn" ? "提醒" : sev;
}

// ---- M002 v0.4.0：挂接来源 / 门控 / 完成分析（ADR-013 聚合学科子任务级判定）----
/** 挂接来源（`LinkDTO.source`）。 */
export const LINK_SOURCE_TEXT: Record<string, string> = {
  ai: "AI 建议",
  manual: "手工挂接",
};

/** 完成分析结论（`Conclusion`，与后端枚举严格一致）。 */
export const CONCLUSION_TEXT: Record<string, string> = {
  完成: "完成",
  部分完成: "部分完成",
  未完成: "未完成",
  无法判断: "无法判断",
};

/** 完成分析状态（`AnalysisItem.status`）。 */
export const ANALYSIS_STATUS_TEXT: Record<string, string> = {
  draft: "草稿",
  confirmed: "已确认",
};

export function conclusionText(v: string): string {
  return CONCLUSION_TEXT[v] ?? v;
}

export function analysisStatusText(v: string): string {
  return ANALYSIS_STATUS_TEXT[v] ?? v;
}

/** 单条挂接状态文案（confirmed > rejected > 待复核/待确认）。 */
export function linkStatusText(link: {
  confirmed_at?: string | null;
  rejected_at?: string | null;
  source: string;
}): string {
  if (link.rejected_at) return "已驳回";
  if (link.confirmed_at) return "已确认";
  return link.source === "ai" ? "待复核" : "待确认";
}

/** 门控摘要（`GateStatusDTO`）：`共 N 张 · 待复核 M 张`。 */
export function gateSummary(gate: {
  total_photos: number;
  pending_photos: number;
}): string {
  return `共 ${gate.total_photos} 张 · 待复核 ${gate.pending_photos} 张`;
}

/** 聚合窗口显示名：优先后端 `display_name`（「第 N 周」/「周末作业」）。 */
export function windowDisplayName(
  displayName?: string | null,
  windowType?: string | null
): string {
  if (displayName) return displayName;
  if (windowType === "weekend") return "周末作业";
  if (windowType === "holiday") return "假期作业";
  return "当日作业";
}

export function formatTime(iso?: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("zh-CN", { hour12: false });
}

export function localInputValue(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function toIso(datetimeLocal: string): string | null {
  return datetimeLocal ? new Date(datetimeLocal).toISOString() : null;
}
