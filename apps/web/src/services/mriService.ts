import type { MriJob, MriResult } from "../types/api";
import { apiClient } from "./apiClient";

export type MriModality = "flair" | "t1" | "t1ce" | "t2";
export type MriFileSet = Record<MriModality, File>;

export const mriService = {
  submit: (
    files: MriFileSet,
    signal?: AbortSignal,
    onProgress?: (percent: number) => void,
  ) => {
    const data = new FormData();
    (Object.entries(files) as [MriModality, File][]).forEach(
      ([modality, file]) => {
        data.append(modality, file, file.name);
      },
    );
    return apiClient.upload<MriJob>("/mri/segment", {
      data,
      signal,
      onProgress,
    });
  },
  job: (jobId: string, signal?: AbortSignal) =>
    apiClient.request<MriJob>(`/mri/jobs/${jobId}`, { signal }),
  result: (jobId: string, signal?: AbortSignal) =>
    apiClient.request<MriResult>(`/mri/jobs/${jobId}/result`, { signal }),
  download: (jobId: string, signal?: AbortSignal) =>
    apiClient.download(`/mri/jobs/${jobId}/result?download=true`, signal),
};
