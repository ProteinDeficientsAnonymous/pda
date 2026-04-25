// Content API: home, faq, guidelines, and the slug-based "editable pages"
// (donate, volunteer, ...). The backend stores both Quill Delta (Flutter)
// and ProseMirror JSON (React/TipTap); phase 4 sends ProseMirror on writes.
// Read path uses `contentHtml` regardless of which editor produced the row.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import { useAuthStore } from '@/auth/store';

export interface HomePage {
  content: string;
  contentPm: string;
  contentHtml: string;
  updatedAt: string;
}

export interface SimplePage {
  content: string;
  contentPm: string;
  contentHtml: string;
  updatedAt: string;
}

export interface EditablePage {
  slug: string;
  content: string;
  contentPm: string;
  contentHtml: string;
  visibility: 'public' | 'members_only';
  updatedAt: string;
}

interface WireHome {
  content?: string;
  content_pm?: string;
  content_html?: string;
  updated_at: string;
}
interface WireSimple {
  content?: string;
  content_pm?: string;
  content_html?: string;
  updated_at: string;
}
interface WireEditable {
  slug: string;
  content?: string;
  content_pm?: string;
  content_html?: string;
  visibility: 'public' | 'members_only';
  updated_at: string;
}

function mapHome(data: WireHome): HomePage {
  return {
    content: data.content ?? '',
    contentPm: data.content_pm ?? '',
    contentHtml: data.content_html ?? '',
    updatedAt: data.updated_at,
  };
}

function mapSimple(data: WireSimple): SimplePage {
  return {
    content: data.content ?? '',
    contentPm: data.content_pm ?? '',
    contentHtml: data.content_html ?? '',
    updatedAt: data.updated_at,
  };
}

function mapEditable(data: WireEditable): EditablePage {
  return {
    slug: data.slug,
    content: data.content ?? '',
    contentPm: data.content_pm ?? '',
    contentHtml: data.content_html ?? '',
    visibility: data.visibility,
    updatedAt: data.updated_at,
  };
}

async function fetchHome(): Promise<HomePage> {
  const { data } = await apiClient.get<WireHome>('/api/community/home/');
  return mapHome(data);
}

async function fetchSimple(path: string): Promise<SimplePage> {
  const { data } = await apiClient.get<WireSimple>(path);
  return mapSimple(data);
}

async function fetchEditablePage(slug: string): Promise<EditablePage> {
  const { data } = await apiClient.get<WireEditable>(`/api/community/pages/${slug}/`);
  return mapEditable(data);
}

export function useHome() {
  return useQuery({ queryKey: ['home'], queryFn: fetchHome });
}

export function useFaq() {
  return useQuery({
    queryKey: ['faq'],
    queryFn: () => fetchSimple('/api/community/faq/'),
  });
}

export function useGuidelines() {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useQuery({
    queryKey: ['guidelines', { authed: isAuthed }],
    queryFn: () => fetchSimple('/api/community/guidelines/'),
    enabled: isAuthed,
  });
}

export function useEditablePage(slug: string) {
  return useQuery({
    queryKey: ['page', slug],
    queryFn: () => fetchEditablePage(slug),
  });
}

// --- Save mutations. --------------------------------------------------------

export interface HomeUpdate {
  contentPm?: string;
}

export function useUpdateHome() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (patch: HomeUpdate) => {
      const body: Record<string, string> = {};
      if (patch.contentPm !== undefined) body.content_pm = patch.contentPm;
      const { data } = await apiClient.patch<WireHome>('/api/community/home/', body);
      return mapHome(data);
    },
    onSuccess: (home) => {
      qc.setQueryData(['home'], home);
    },
  });
}

function makeSimplePatch(path: string, queryKey: readonly unknown[]) {
  return function useSimpleUpdate() {
    const qc = useQueryClient();
    return useMutation({
      mutationFn: async (contentPm: string) => {
        const { data } = await apiClient.patch<WireSimple>(path, { content_pm: contentPm });
        return mapSimple(data);
      },
      onSuccess: (page) => {
        qc.setQueryData(queryKey, page);
      },
    });
  };
}

export const useUpdateFaq = makeSimplePatch('/api/community/faq/', ['faq']);
// Guidelines cache key includes {authed} — compute it here to keep the
// write invalidation aligned with the read.
export function useUpdateGuidelines() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (contentPm: string) => {
      const { data } = await apiClient.patch<WireSimple>('/api/community/guidelines/', {
        content_pm: contentPm,
      });
      return mapSimple(data);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['guidelines'] });
    },
  });
}

export interface EditablePageUpdate {
  contentPm?: string;
  visibility?: 'public' | 'members_only';
}

export function useUpdateEditablePage(slug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (patch: EditablePageUpdate) => {
      const body: Record<string, string> = {};
      if (patch.contentPm !== undefined) body.content_pm = patch.contentPm;
      if (patch.visibility !== undefined) body.visibility = patch.visibility;
      const { data } = await apiClient.patch<WireEditable>(`/api/community/pages/${slug}/`, body);
      return mapEditable(data);
    },
    onSuccess: (page) => {
      qc.setQueryData(['page', slug], page);
    },
  });
}

// --- Welcome message template (plain text, edited by vetters). --------------

export interface WelcomeTemplate {
  body: string;
  updatedAt: string;
}

interface WireWelcomeTemplate {
  body: string;
  updated_at: string;
}

function mapWelcomeTemplate(data: WireWelcomeTemplate): WelcomeTemplate {
  return { body: data.body, updatedAt: data.updated_at };
}

export function useWelcomeTemplate() {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useQuery({
    queryKey: ['welcome-template'],
    queryFn: async () => {
      const { data } = await apiClient.get<WireWelcomeTemplate>('/api/community/welcome-template/');
      return mapWelcomeTemplate(data);
    },
    enabled: isAuthed,
  });
}

export function useUpdateWelcomeTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: string) => {
      const { data } = await apiClient.patch<WireWelcomeTemplate>(
        '/api/community/welcome-template/',
        { body },
      );
      return mapWelcomeTemplate(data);
    },
    onSuccess: (template) => {
      qc.setQueryData(['welcome-template'], template);
    },
  });
}
