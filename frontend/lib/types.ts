export type SheetStructure = {
  name: string;
  row_count: number;
  data_row_count: number;
  column_count: number;
  headers: string[];
  headers_truncated: boolean;
};

export type WorkbookStructure = {
  file_type: string;
  sheet_count: number;
  row_count: number;
  sheets: SheetStructure[];
};

export type DocumentVersion = {
  id: string;
  version_number: number;
  label: string;
  sha256: string;
  created_at: string;
  structure: WorkbookStructure;
};

export type DocumentRecord = {
  id: string;
  original_filename: string;
  extension: string;
  byte_size: number;
  sha256: string;
  current_version_number: number;
  created_at: string;
  version: DocumentVersion | null;
};

export type UploadItem = {
  filename: string;
  status: "stored" | "rejected";
  document: DocumentRecord | null;
  error: { code: string; message: string } | null;
};

export type UploadBatch = {
  items: UploadItem[];
};

export type FileTypeInfo = {
  extension: string;
  label: string;
  kind: string;
  enabled: boolean;
};
