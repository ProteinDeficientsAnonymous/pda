// Docs API. Reads used everywhere; writes gated by manage_documents.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

export interface DocSummary {
  id: string;
  title: string;
  displayOrder: number;
  updatedAt: string;
}

export interface DocFolder {
  id: string;
  name: string;
  parentId: string | null;
  displayOrder: number;
  children: DocFolder[];
  documents: DocSummary[];
}

export interface Document {
  id: string;
  title: string;
  /** Legacy Quill Delta JSON (Flutter). */
  content: string;
  /** ProseMirror JSON (TipTap). */
  contentPm: string;
  contentHtml: string;
  folderId: string;
  displayOrder: number;
  createdById: string | null;
  createdAt: string;
  updatedAt: string;
}

interface WireSummary {
  id: string;
  title: string;
  display_order: number;
  updated_at: string;
}

interface WireFolder {
  id: string;
  name: string;
  parent_id: string | null;
  display_order: number;
  children: WireFolder[];
  documents: WireSummary[];
}

interface WireDocument {
  id: string;
  title: string;
  content: string;
  content_pm?: string;
  content_html: string;
  folder_id: string;
  display_order: number;
  created_by_id: string | null;
  created_at: string;
  updated_at: string;
}

function mapSummary(s: WireSummary): DocSummary {
  return {
    id: s.id,
    title: s.title,
    displayOrder: s.display_order,
    updatedAt: s.updated_at,
  };
}

function mapFolder(f: WireFolder): DocFolder {
  return {
    id: f.id,
    name: f.name,
    parentId: f.parent_id,
    displayOrder: f.display_order,
    children: f.children.map(mapFolder),
    documents: f.documents.map(mapSummary),
  };
}

function mapDocument(d: WireDocument): Document {
  return {
    id: d.id,
    title: d.title,
    content: d.content,
    contentPm: d.content_pm ?? '',
    contentHtml: d.content_html,
    folderId: d.folder_id,
    displayOrder: d.display_order,
    createdById: d.created_by_id,
    createdAt: d.created_at,
    updatedAt: d.updated_at,
  };
}

export function useDocFolders() {
  return useQuery({
    queryKey: ['docs', 'folders'],
    queryFn: async () => {
      const { data } = await apiClient.get<WireFolder[]>('/api/community/docs/folders/');
      return data.map(mapFolder);
    },
  });
}

export function useDocument(id: string | undefined) {
  return useQuery({
    queryKey: ['docs', 'detail', id ?? ''],
    queryFn: async () => {
      const { data } = await apiClient.get<WireDocument>(`/api/community/docs/${id ?? ''}/`);
      return mapDocument(data);
    },
    enabled: Boolean(id),
  });
}

export interface DocumentUpdate {
  title?: string;
  contentPm?: string;
}

export function useUpdateDocument(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (patch: DocumentUpdate) => {
      const body: Record<string, string> = {};
      if (patch.title !== undefined) body.title = patch.title;
      if (patch.contentPm !== undefined) body.content_pm = patch.contentPm;
      const { data } = await apiClient.patch<WireDocument>(`/api/community/docs/${id}/`, body);
      return mapDocument(data);
    },
    onSuccess: (doc) => {
      qc.setQueryData(['docs', 'detail', id], doc);
      void qc.invalidateQueries({ queryKey: ['docs', 'folders'] });
    },
  });
}
