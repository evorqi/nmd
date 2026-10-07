import type { FileTypeInfo, UploadBatch } from "@/lib/types";

export class ApiError extends Error {
  readonly code: string;

  constructor(message: string, code = "request_failed") {
    super(message);
    this.name = "ApiError";
    this.code = code;
  }
}

async function readError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as { code?: string; message?: string };
    return new ApiError(body.message ?? "درخواست ناموفق بود.", body.code ?? "request_failed");
  } catch {
    return new ApiError("درخواست ناموفق بود.");
  }
}

export async function fetchFileTypes(): Promise<FileTypeInfo[]> {
  const response = await fetch("/api/file-types");
  if (!response.ok) {
    throw await readError(response);
  }
  const body = (await response.json()) as { items: FileTypeInfo[] };
  return body.items;
}

export async function uploadFiles(files: File[]): Promise<UploadBatch> {
  const body = new FormData();
  for (const file of files) {
    body.append("files", file);
  }
  const response = await fetch("/api/uploads", { method: "POST", body });
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as UploadBatch;
}
