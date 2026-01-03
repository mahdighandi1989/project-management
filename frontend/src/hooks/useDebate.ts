/**
 * Hook for managing debate state
 */

import { create } from 'zustand';
import { debateApi, DebateResponse, DebateDetail, RoundResponse } from '@/services/api';

interface DebateState {
  // Current debate
  currentDebate: DebateDetail | null;
  isLoading: boolean;
  error: string | null;

  // Debate list
  debates: DebateResponse[];

  // Actions
  createDebate: (prompt: string, mode?: string, models?: string[]) => Promise<DebateResponse>;
  loadDebate: (id: string) => Promise<void>;
  runRound: (roundNumber?: number, context?: string) => Promise<RoundResponse[]>;
  runFullDebate: () => Promise<void>;
  runScoring: () => Promise<void>;
  runJudging: () => Promise<void>;
  runSummary: () => Promise<void>;
  loadDebates: () => Promise<void>;
  clearError: () => void;
  reset: () => void;
}

export const useDebate = create<DebateState>((set, get) => ({
  currentDebate: null,
  isLoading: false,
  error: null,
  debates: [],

  createDebate: async (prompt: string, mode = 'auto', models?: string[]) => {
    set({ isLoading: true, error: null });
    try {
      const response = await debateApi.create(prompt, mode, models);
      const debate = response.data;

      // Load full details
      const detailResponse = await debateApi.get(debate.id);
      set({ currentDebate: detailResponse.data, isLoading: false });

      return debate;
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'خطا در ایجاد مناظره';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  loadDebate: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await debateApi.get(id);
      set({ currentDebate: response.data, isLoading: false });
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'خطا در بارگذاری مناظره';
      set({ error: message, isLoading: false });
    }
  },

  runRound: async (roundNumber = 1, context?: string) => {
    const { currentDebate } = get();
    if (!currentDebate) throw new Error('No debate selected');

    set({ isLoading: true, error: null });
    try {
      const response = await debateApi.runRound(currentDebate.id, roundNumber, context);

      // Reload debate to get updated state
      const detailResponse = await debateApi.get(currentDebate.id);
      set({ currentDebate: detailResponse.data, isLoading: false });

      return response.data;
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'خطا در اجرای دور';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  runFullDebate: async () => {
    const { currentDebate } = get();
    if (!currentDebate) throw new Error('No debate selected');

    set({ isLoading: true, error: null });
    try {
      await debateApi.runFull(currentDebate.id);

      // Poll for completion
      const pollInterval = setInterval(async () => {
        const response = await debateApi.get(currentDebate.id);
        set({ currentDebate: response.data });

        if (response.data.status === 'completed' || response.data.status === 'failed') {
          clearInterval(pollInterval);
          set({ isLoading: false });
        }
      }, 2000);

    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'خطا در اجرای مناظره';
      set({ error: message, isLoading: false });
    }
  },

  runScoring: async () => {
    const { currentDebate } = get();
    if (!currentDebate) throw new Error('No debate selected');

    set({ isLoading: true, error: null });
    try {
      await debateApi.score(currentDebate.id);

      // Reload debate
      const response = await debateApi.get(currentDebate.id);
      set({ currentDebate: response.data, isLoading: false });
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'خطا در امتیازدهی';
      set({ error: message, isLoading: false });
    }
  },

  runJudging: async () => {
    const { currentDebate } = get();
    if (!currentDebate) throw new Error('No debate selected');

    set({ isLoading: true, error: null });
    try {
      await debateApi.judge(currentDebate.id);

      // Reload debate
      const response = await debateApi.get(currentDebate.id);
      set({ currentDebate: response.data, isLoading: false });
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'خطا در داوری';
      set({ error: message, isLoading: false });
    }
  },

  runSummary: async () => {
    const { currentDebate } = get();
    if (!currentDebate) throw new Error('No debate selected');

    set({ isLoading: true, error: null });
    try {
      await debateApi.summary(currentDebate.id);

      // Reload debate
      const response = await debateApi.get(currentDebate.id);
      set({ currentDebate: response.data, isLoading: false });
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'خطا در خلاصه‌نویسی';
      set({ error: message, isLoading: false });
    }
  },

  loadDebates: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await debateApi.list();
      set({ debates: response.data, isLoading: false });
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'خطا در بارگذاری لیست';
      set({ error: message, isLoading: false });
    }
  },

  clearError: () => set({ error: null }),

  reset: () => set({
    currentDebate: null,
    isLoading: false,
    error: null,
  }),
}));
