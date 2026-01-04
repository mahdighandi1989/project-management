/**
 * File Upload Component - کامپوننت آپلود فایل
 * برای آپلود فایل‌ها در مناظره و پروژه‌ها
 */

'use client';

import { useState, useRef, useCallback } from 'react';
import {
  CloudArrowUpIcon,
  DocumentIcon,
  PhotoIcon,
  FilmIcon,
  MusicalNoteIcon,
  CodeBracketIcon,
  TrashIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';

// Types
interface UploadedFile {
  id: string;
  file: File;
  name: string;
  size: number;
  type: string;
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  error?: string;
  result?: {
    file_id: string;
    path: string;
    github?: {
      url?: string;
    };
  };
}

interface FileUploadProps {
  entityType: 'debate' | 'project';
  entityId?: string;
  onFilesUploaded?: (files: UploadedFile[]) => void;
  maxFiles?: number;
  maxSizeMB?: number;
  acceptedTypes?: string[];
  storeInGithub?: boolean;
}

// File type icons
const getFileIcon = (mimeType: string) => {
  if (mimeType.startsWith('image/')) return PhotoIcon;
  if (mimeType.startsWith('video/')) return FilmIcon;
  if (mimeType.startsWith('audio/')) return MusicalNoteIcon;
  if (
    mimeType.includes('javascript') ||
    mimeType.includes('python') ||
    mimeType.includes('java') ||
    mimeType.includes('text/') ||
    mimeType.includes('json')
  ) {
    return CodeBracketIcon;
  }
  return DocumentIcon;
};

// Format file size
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

export default function FileUpload({
  entityType,
  entityId,
  onFilesUploaded,
  maxFiles = 10,
  maxSizeMB = 50,
  acceptedTypes,
  storeInGithub = true,
}: FileUploadProps) {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // API URL
  const getApiUrl = () => {
    if (typeof window !== 'undefined') {
      const runtimeUrl = (window as any).__NEXT_PUBLIC_API_URL__;
      if (runtimeUrl) return runtimeUrl;
    }
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  };

  // Handle file selection
  const handleFiles = useCallback(
    (newFiles: FileList | File[]) => {
      const fileArray = Array.from(newFiles);
      const maxSizeBytes = maxSizeMB * 1024 * 1024;

      const validFiles: UploadedFile[] = [];

      for (const file of fileArray) {
        if (files.length + validFiles.length >= maxFiles) {
          alert(`حداکثر ${maxFiles} فایل می‌توانید آپلود کنید`);
          break;
        }

        if (file.size > maxSizeBytes) {
          alert(`فایل ${file.name} بیش از ${maxSizeMB}MB است`);
          continue;
        }

        validFiles.push({
          id: `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          file,
          name: file.name,
          size: file.size,
          type: file.type || 'application/octet-stream',
          progress: 0,
          status: 'pending',
        });
      }

      if (validFiles.length > 0) {
        setFiles((prev) => [...prev, ...validFiles]);
      }
    },
    [files.length, maxFiles, maxSizeMB]
  );

  // Drag and drop handlers
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const droppedFiles = e.dataTransfer.files;
    if (droppedFiles.length > 0) {
      handleFiles(droppedFiles);
    }
  };

  // Remove file
  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  // Upload single file
  const uploadFile = async (uploadFile: UploadedFile): Promise<UploadedFile> => {
    const formData = new FormData();
    formData.append('file', uploadFile.file);
    formData.append('analysis_type', 'none');
    formData.append('store_in_github', String(storeInGithub));

    if (entityType === 'debate' && entityId) {
      formData.append('debate_id', entityId);
    } else if (entityType === 'project' && entityId) {
      formData.append('project_id', entityId);
    }

    try {
      const response = await fetch(`${getApiUrl()}/api/orchestrator/upload-for-analysis`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const result = await response.json();

      return {
        ...uploadFile,
        progress: 100,
        status: 'completed',
        result: {
          file_id: result.file_id,
          path: result.local_path,
          github: result.github,
        },
      };
    } catch (error: any) {
      return {
        ...uploadFile,
        progress: 0,
        status: 'error',
        error: error.message || 'خطا در آپلود',
      };
    }
  };

  // Upload all pending files
  const uploadAllFiles = async () => {
    const pendingFiles = files.filter((f) => f.status === 'pending');
    if (pendingFiles.length === 0) return;

    const updatedFiles = [...files];

    for (let i = 0; i < pendingFiles.length; i++) {
      const file = pendingFiles[i];
      const fileIndex = updatedFiles.findIndex((f) => f.id === file.id);

      // Update to uploading
      updatedFiles[fileIndex] = { ...updatedFiles[fileIndex], status: 'uploading', progress: 50 };
      setFiles([...updatedFiles]);

      // Upload
      const result = await uploadFile(file);
      updatedFiles[fileIndex] = result;
      setFiles([...updatedFiles]);
    }

    // Callback
    if (onFilesUploaded) {
      onFilesUploaded(updatedFiles.filter((f) => f.status === 'completed'));
    }
  };

  // Get status icon
  const getStatusIcon = (status: UploadedFile['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="w-5 h-5 text-green-500" />;
      case 'error':
        return <ExclamationCircleIcon className="w-5 h-5 text-red-500" />;
      case 'uploading':
        return <div className="w-5 h-5 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />;
      default:
        return null;
    }
  };

  const pendingCount = files.filter((f) => f.status === 'pending').length;
  const completedCount = files.filter((f) => f.status === 'completed').length;

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        className={`
          relative border-2 border-dashed rounded-xl p-6 transition-all cursor-pointer
          ${isDragging
            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
            : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
          }
        `}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={acceptedTypes?.join(',')}
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
          className="hidden"
        />

        <div className="flex flex-col items-center gap-3 text-center">
          <CloudArrowUpIcon className={`w-12 h-12 ${isDragging ? 'text-primary-500' : 'text-gray-400'}`} />
          <div>
            <p className="text-gray-700 dark:text-gray-300 font-medium">
              فایل‌ها را اینجا رها کنید
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              یا کلیک کنید برای انتخاب
            </p>
          </div>
          <p className="text-xs text-gray-400">
            حداکثر {maxFiles} فایل • هر فایل تا {maxSizeMB}MB
          </p>
        </div>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">
              {files.length} فایل {completedCount > 0 && `(${completedCount} آپلود شده)`}
            </span>
            {pendingCount > 0 && (
              <button
                onClick={uploadAllFiles}
                className="btn btn-primary btn-sm"
              >
                آپلود {pendingCount} فایل
              </button>
            )}
          </div>

          <div className="space-y-2 max-h-60 overflow-y-auto">
            {files.map((file) => {
              const FileIcon = getFileIcon(file.type);
              return (
                <div
                  key={file.id}
                  className={`
                    flex items-center gap-3 p-3 rounded-lg border
                    ${file.status === 'error'
                      ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                      : file.status === 'completed'
                      ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                      : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700'
                    }
                  `}
                >
                  <FileIcon className="w-8 h-8 text-gray-400 flex-shrink-0" />

                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {file.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatFileSize(file.size)}
                      {file.error && <span className="text-red-500 mr-2">• {file.error}</span>}
                    </p>
                    {file.status === 'uploading' && (
                      <div className="mt-1 h-1 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary-500 transition-all"
                          style={{ width: `${file.progress}%` }}
                        />
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {getStatusIcon(file.status)}
                    {file.status !== 'uploading' && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeFile(file.id);
                        }}
                        className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                      >
                        <TrashIcon className="w-4 h-4 text-gray-400" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Supported formats */}
      <p className="text-xs text-gray-400 text-center">
        فرمت‌های پشتیبانی: متن، کد، تصویر، PDF، ویدیو، صوت و ...
      </p>
    </div>
  );
}
