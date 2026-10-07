"use client";

import { useEffect, useMemo, useState } from "react";
import { ApiError, fetchFileTypes, uploadFiles } from "@/lib/api";
import type { FileTypeInfo, UploadBatch } from "@/lib/types";

const numberFormat = new Intl.NumberFormat("fa-IR");
const sizeFormat = new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 1 });

function formatCount(value: number): string {
  return numberFormat.format(value);
}

function formatBytes(size: number): string {
  if (size < 1024) {
    return `${formatCount(size)} بایت`;
  }
  if (size < 1024 * 1024) {
    return `${sizeFormat.format(size / 1024)} کیلوبایت`;
  }
  return `${sizeFormat.format(size / (1024 * 1024))} مگابایت`;
}

function fileKey(file: File): string {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

export function UploadWorkspace() {
  const [selected, setSelected] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [batch, setBatch] = useState<UploadBatch | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [fileTypes, setFileTypes] = useState<FileTypeInfo[]>([]);

  useEffect(() => {
    let active = true;
    fetchFileTypes()
      .then((items) => {
        if (active) {
          setFileTypes(items);
        }
      })
      .catch(() => {
        if (active) {
          setFileTypes([]);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const enabled = useMemo(() => fileTypes.filter((item) => item.enabled), [fileTypes]);
  const disabled = useMemo(() => fileTypes.filter((item) => !item.enabled), [fileTypes]);

  function addFiles(list: FileList | File[]) {
    const incoming = Array.from(list);
    setSelected((current) => {
      const seen = new Set(current.map(fileKey));
      const next = [...current];
      for (const file of incoming) {
        const key = fileKey(file);
        if (!seen.has(key)) {
          seen.add(key);
          next.push(file);
        }
      }
      return next;
    });
  }

  async function onSubmit() {
    if (selected.length === 0 || uploading) {
      return;
    }
    setUploading(true);
    setRequestError(null);
    try {
      setBatch(await uploadFiles(selected));
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "ارتباط با سرور برقرار نشد.";
      setRequestError(message);
      setBatch(null);
    } finally {
      setUploading(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="mark" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
          </div>
          <div>
            <p className="eyebrow">nmd</p>
            <h1>ورود فایل</h1>
          </div>
        </div>
        <div>
          <p className="lede">
            فایل اکسل یا CSV را بدهید. ساختار شیت‌ها، عنوان ستون‌ها و تعداد ردیف‌ها خوانده می‌شود.
          </p>
          <p className="promise">نسخه اصلی ذخیره می‌شود و بازنویسی نمی‌شود.</p>
        </div>
      </header>

      <section className="workspace">
        <aside className="panel">
          <label
            className={dragging ? "dropzone hot" : "dropzone"}
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              if (event.dataTransfer.files.length > 0) {
                addFiles(event.dataTransfer.files);
              }
            }}
          >
            <span>
              <strong>فایل را اینجا رها کنید</strong>
              <p>یک یا چند فایل xlsx، xls یا csv</p>
            </span>
            <input
              className="file-input"
              data-testid="file-input"
              type="file"
              multiple
              accept=".xlsx,.xls,.csv"
              onChange={(event) => {
                if (event.target.files) {
                  addFiles(event.target.files);
                }
                event.target.value = "";
              }}
            />
          </label>

          {selected.length > 0 ? (
            <div className="file-list">
              {selected.map((file) => (
                <div className="file-row" key={fileKey(file)}>
                  <b>{file.name}</b>
                  <button
                    className="icon-button"
                    type="button"
                    onClick={() => setSelected((current) => current.filter((item) => fileKey(item) !== fileKey(file)))}
                  >
                    حذف
                  </button>
                </div>
              ))}
            </div>
          ) : null}

          <button
            className="primary"
            data-testid="upload-button"
            type="button"
            disabled={selected.length === 0 || uploading}
            onClick={() => {
              void onSubmit();
            }}
          >
            {uploading ? "در حال خواندن..." : "خواندن ساختار"}
          </button>

          <div className="support" aria-label="نوع‌های فایل">
            {(enabled.length > 0 ? enabled.map((item) => item.extension) : ["xlsx", "xls", "csv"]).map((extension) => (
              <span className="chip" key={extension}>
                {extension}
              </span>
            ))}
            {disabled.map((item) => (
              <span className="chip off" key={item.extension} title="در نسخه اول فعال نیست">
                {item.extension}
              </span>
            ))}
          </div>
        </aside>

        <section className="results" aria-live="polite" data-testid="results">
          {requestError ? <div className="banner">{requestError}</div> : null}
          {batch === null && requestError === null ? (
            <div className="empty-state">
              <h2>هنوز فایلی خوانده نشده</h2>
              <p className="empty-copy">بعد از خواندن، نام شیت‌ها و عنوان ستون‌ها اینجا نشان داده می‌شود.</p>
            </div>
          ) : null}
          {batch?.items.map((item, index) => {
            if (item.status === "rejected" || item.document?.version == null) {
              return (
                <article className="result-card rejected" key={`${item.filename}-${index}`}>
                  <div className="section-title">
                    <h2>{item.filename || "فایل بدون نام"}</h2>
                    <span className="badge bad">رد شد</span>
                  </div>
                  <p className="meta">{item.error?.message ?? "این فایل خوانده نشد."}</p>
                </article>
              );
            }
            const version = item.document.version;
            return (
              <article className="result-card" key={item.document.id}>
                <div className="section-title">
                  <h2>{item.document.original_filename}</h2>
                  <span className="badge">نسخه اصلی</span>
                </div>
                <p className="meta">
                  {item.document.extension} · {formatBytes(item.document.byte_size)} ·{" "}
                  {formatCount(version.structure.sheet_count)} شیت · {formatCount(version.structure.row_count)} ردیف
                  غیرخالی
                </p>
                <p className="meta" title={version.sha256}>
                  شناسه نسخه {version.sha256.slice(0, 12)}
                </p>
                <div className="sheet-grid">
                  {version.structure.sheets.map((sheet) => (
                    <section className="sheet-card" key={`${item.document?.id}-${sheet.name}`}>
                      <div className="sheet-head">
                        <h3>{sheet.name}</h3>
                        <span>{formatCount(sheet.column_count)} ستون</span>
                      </div>
                      <div className="stats">
                        <span>{formatCount(sheet.row_count)} ردیف غیرخالی</span>
                        <span>{formatCount(sheet.data_row_count)} ردیف داده</span>
                      </div>
                      {sheet.row_count === 0 ? <p>این شیت داده‌ای ندارد.</p> : null}
                      {sheet.headers_truncated ? <p>برخی عنوان‌ها در خلاصه کوتاه شده‌اند. فایل اصلی کامل است.</p> : null}
                      {sheet.headers.length > 0 ? (
                        <div className="headers">
                          {sheet.headers.map((header, headerIndex) => (
                            <span
                              className={header === "" ? "header-chip missing" : "header-chip"}
                              key={`${sheet.name}-${headerIndex}`}
                            >
                              {header === "" ? "بدون عنوان" : header}
                            </span>
                          ))}
                        </div>
                      ) : null}
                    </section>
                  ))}
                </div>
              </article>
            );
          })}
        </section>
      </section>
    </main>
  );
}
