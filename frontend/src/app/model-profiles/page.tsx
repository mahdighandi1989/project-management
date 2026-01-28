'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ModelProfile {
  model_id: string;
  provider: string;
  display_name: string;
  overall_score: number;
  accuracy_score: number;
  completeness_score: number;
  speed_score: number;
  reliability_score: number;
  tier: string;
  rank: number;
  total_analyses: number;
  total_tasks: number;
  avg_response_time: number;
  last_activity: string | null;
}

interface ProfileDetail {
  model_id: string;
  provider: string;
  display_name: string;
  scores: {
    overall: number;
    accuracy: number;
    completeness: number;
    speed: number;
    reliability: number;
    code_quality: number;
    reasoning: number;
  };
  stats: {
    total_analyses: number;
    total_tasks: number;
    total_debates: number;
    correct_findings: number;
    missed_issues: number;
    false_positives: number;
  };
  performance: {
    avg_response_time: number;
    total_tokens_used: number;
    total_cost: number;
  };
  ranking: {
    rank: number;
    tier: string;
  };
  capabilities: {
    strengths: string[];
    weaknesses: string[];
  };
  timestamps: {
    created_at: string | null;
    updated_at: string | null;
    last_activity: string | null;
  };
  validation_history: any[];
}

interface Leaderboard {
  [key: string]: {
    label: string;
    model_id: string;
    display_name: string;
    score: number;
    tier: string;
  };
}

export default function ModelProfilesPage() {
  const [profiles, setProfiles] = useState<ModelProfile[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<ProfileDetail | null>(null);
  const [leaderboard, setLeaderboard] = useState<Leaderboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [sortBy, setSortBy] = useState('overall_score');
  const [sortOrder, setSortOrder] = useState('desc');
  const [activeTab, setActiveTab] = useState<'rankings' | 'leaderboard' | 'history'>('rankings');
  const [isFallbackData, setIsFallbackData] = useState(false);
  const [dataNote, setDataNote] = useState<string | null>(null);

  // داده‌های پیش‌فرض
  const defaultProfiles: ModelProfile[] = [
    {model_id: "gpt-4", provider: "openai", display_name: "GPT-4", tier: "S", overall_score: 92.5, accuracy_score: 95, completeness_score: 90, speed_score: 88, reliability_score: 94, total_analyses: 0, total_tasks: 0, avg_response_time: 1200, last_activity: null, rank: 1},
    {model_id: "gpt-4o", provider: "openai", display_name: "GPT-4o", tier: "S", overall_score: 91.0, accuracy_score: 93, completeness_score: 89, speed_score: 95, reliability_score: 92, total_analyses: 0, total_tasks: 0, avg_response_time: 800, last_activity: null, rank: 2},
    {model_id: "claude-3-opus", provider: "anthropic", display_name: "Claude 3 Opus", tier: "S", overall_score: 90.5, accuracy_score: 94, completeness_score: 92, speed_score: 82, reliability_score: 93, total_analyses: 0, total_tasks: 0, avg_response_time: 1500, last_activity: null, rank: 3},
    {model_id: "gpt-4o-mini", provider: "openai", display_name: "GPT-4o Mini", tier: "A", overall_score: 85.0, accuracy_score: 86, completeness_score: 83, speed_score: 92, reliability_score: 88, total_analyses: 0, total_tasks: 0, avg_response_time: 500, last_activity: null, rank: 4},
    {model_id: "claude-3-sonnet", provider: "anthropic", display_name: "Claude 3 Sonnet", tier: "A", overall_score: 84.0, accuracy_score: 88, completeness_score: 85, speed_score: 80, reliability_score: 86, total_analyses: 0, total_tasks: 0, avg_response_time: 1000, last_activity: null, rank: 5},
    {model_id: "deepseek-chat", provider: "deepseek", display_name: "DeepSeek Chat", tier: "B", overall_score: 78.0, accuracy_score: 80, completeness_score: 76, speed_score: 82, reliability_score: 78, total_analyses: 0, total_tasks: 0, avg_response_time: 700, last_activity: null, rank: 6},
  ];

  const defaultLeaderboard: Leaderboard = {
    best_accuracy: {label: "بهترین دقت", model_id: "gpt-4", display_name: "GPT-4", score: 95, tier: "S"},
    best_speed: {label: "سریع‌ترین", model_id: "gpt-4o", display_name: "GPT-4o", score: 95, tier: "S"},
    best_reliability: {label: "قابل‌اطمینان‌ترین", model_id: "gpt-4", display_name: "GPT-4", score: 94, tier: "S"},
    best_code_quality: {label: "بهترین کیفیت کد", model_id: "claude-3-opus", display_name: "Claude 3 Opus", score: 92, tier: "S"},
    most_active: {label: "فعال‌ترین", model_id: "gpt-4o-mini", display_name: "GPT-4o Mini", score: 0, tier: "A"},
  };

  useEffect(() => {
    loadProfiles();
    loadLeaderboard();
  }, [sortBy, sortOrder]);

  const loadProfiles = async () => {
    setLoading(true);
    try {
      // درخواست بدون fallback برای دیدن داده‌های واقعی
      const res = await fetch(`${API_BASE}/api/models/profiles?sort_by=${sortBy}&order=${sortOrder}&use_fallback=false`);
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.profiles?.length > 0) {
          setProfiles(data.profiles);
          setIsFallbackData(data.is_fallback || false);
          setDataNote(data.note || null);
          return;
        } else if (data.note) {
          // پروفایل واقعی نیست، استفاده از پیش‌فرض
          setDataNote(data.note);
        }
      }
      // اگر پاسخ موفق نبود، داده‌های پیش‌فرض
      setProfiles(defaultProfiles);
      setIsFallbackData(true);
      setDataNote("داده‌های نمایشی - هنوز تحلیلی انجام نشده");
    } catch (e) {
      console.log('Using default profiles');
      setProfiles(defaultProfiles);
      setIsFallbackData(true);
      setDataNote("خطا در اتصال به سرور - نمایش داده‌های پیش‌فرض");
    } finally {
      setLoading(false);
    }
  };

  const loadLeaderboard = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/models/leaderboard`);
      if (res.ok) {
        const data = await res.json();
        if (data.success && Object.keys(data.leaderboard || {}).length > 0) {
          setLeaderboard(data.leaderboard);
          // اگر همه مدل‌ها 0 تسک دارند، نمایشی است
          const anyActive = Object.values(data.leaderboard).some((l: any) => l.score > 0);
          if (!anyActive) {
            setIsFallbackData(true);
          }
          return;
        }
      }
      setLeaderboard(defaultLeaderboard);
      setIsFallbackData(true);
    } catch (e) {
      console.log('Using default leaderboard');
      setLeaderboard(defaultLeaderboard);
      setIsFallbackData(true);
    }
  };

  const loadProfileDetail = async (modelId: string) => {
    setDetailLoading(true);
    try {
      const encodedId = encodeURIComponent(modelId);
      const res = await fetch(`${API_BASE}/api/models/profiles/${encodedId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setSelectedProfile(data.profile);
          return;
        }
      }
      // استفاده از پیش‌فرض
      const found = defaultProfiles.find(p => p.model_id === modelId);
      if (found) {
        setSelectedProfile({
          model_id: found.model_id,
          provider: found.provider,
          display_name: found.display_name,
          scores: {overall: found.overall_score, accuracy: found.accuracy_score, completeness: found.completeness_score, speed: found.speed_score, reliability: found.reliability_score, code_quality: 80, reasoning: 80},
          stats: {total_analyses: 0, total_tasks: 0, total_debates: 0, correct_findings: 0, missed_issues: 0, false_positives: 0},
          performance: {avg_response_time: found.avg_response_time, total_tokens_used: 0, total_cost: 0},
          ranking: {rank: found.rank, tier: found.tier},
          capabilities: {strengths: [], weaknesses: []},
          timestamps: {created_at: null, updated_at: null, last_activity: null},
          validation_history: [],
        } as ProfileDetail);
      }
    } catch (e) {
      console.log('Using default profile detail');
      const found = defaultProfiles.find(p => p.model_id === modelId);
      if (found) {
        setSelectedProfile({
          model_id: found.model_id,
          provider: found.provider,
          display_name: found.display_name,
          scores: {overall: found.overall_score, accuracy: found.accuracy_score, completeness: found.completeness_score, speed: found.speed_score, reliability: found.reliability_score, code_quality: 80, reasoning: 80},
          stats: {total_analyses: 0, total_tasks: 0, total_debates: 0, correct_findings: 0, missed_issues: 0, false_positives: 0},
          performance: {avg_response_time: found.avg_response_time, total_tokens_used: 0, total_cost: 0},
          ranking: {rank: found.rank, tier: found.tier},
          capabilities: {strengths: [], weaknesses: []},
          timestamps: {created_at: null, updated_at: null, last_activity: null},
          validation_history: [],
        } as ProfileDetail);
      }
    } finally {
      setDetailLoading(false);
    }
  };

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'S': return 'bg-gradient-to-r from-yellow-400 to-yellow-600 text-white shadow-lg shadow-yellow-500/30';
      case 'A': return 'bg-gradient-to-r from-green-500 to-green-600 text-white shadow-lg shadow-green-500/30';
      case 'B': return 'bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-lg shadow-blue-500/30';
      case 'C': return 'bg-gradient-to-r from-orange-400 to-orange-500 text-white';
      case 'D': return 'bg-gradient-to-r from-red-400 to-red-500 text-white';
      case 'F': return 'bg-gradient-to-r from-gray-500 to-gray-600 text-white';
      default: return 'bg-gray-400 text-white';
    }
  };

  const getTierBadge = (tier: string) => {
    switch (tier) {
      case 'S': return '🏆';
      case 'A': return '🥇';
      case 'B': return '🥈';
      case 'C': return '🥉';
      case 'D': return '📉';
      case 'F': return '⚠️';
      default: return '❓';
    }
  };

  const getProviderIcon = (provider: string) => {
    switch (provider.toLowerCase()) {
      case 'openai': return '🟢';
      case 'anthropic': return '🟣';
      case 'google': return '🔵';
      case 'deepseek': return '🔷';
      default: return '⚪';
    }
  };

  const getLeaderboardIcon = (key: string) => {
    switch (key) {
      case 'best_accuracy': return '🎯';
      case 'best_speed': return '⚡';
      case 'best_reliability': return '🛡️';
      case 'best_code_quality': return '💎';
      case 'most_active': return '🔥';
      default: return '🏅';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 dark:from-gray-900 dark:to-gray-800" dir="rtl">
      {/* هدر */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/" className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                🏠 خانه
              </Link>
              <span className="text-gray-300 dark:text-gray-600">/</span>
              <h1 className="text-xl font-bold text-gray-800 dark:text-white flex items-center gap-2">
                <span>🤖</span> پروفایل مدل‌های AI (نمرات تجمعی)
              </h1>
            </div>
            <button
              onClick={() => { loadProfiles(); loadLeaderboard(); }}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 flex items-center gap-2"
            >
              <span>🔄</span> بروزرسانی
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* هشدار داده‌های نمایشی */}
        {isFallbackData && (
          <div className="mb-6 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-300 dark:border-yellow-700 rounded-xl p-4">
            <div className="flex items-center gap-3">
              <span className="text-2xl">⚠️</span>
              <div>
                <h4 className="font-bold text-yellow-800 dark:text-yellow-400">داده‌های نمایشی</h4>
                <p className="text-sm text-yellow-700 dark:text-yellow-500">
                  {dataNote || "این داده‌ها نمایشی هستند. برای مشاهده نمرات واقعی، ابتدا تحلیل سلامت را روی یک پروژه اجرا کنید."}
                </p>
                <p className="text-xs text-yellow-600 dark:text-yellow-600 mt-1">
                  نمرات واقعی بر اساس عملکرد مدل‌ها در تحلیل‌های سلامت پروژه محاسبه می‌شوند.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* تب‌ها */}
        <div className="flex gap-2 mb-6 bg-white dark:bg-gray-800 rounded-xl p-2 shadow">
          <button
            onClick={() => setActiveTab('rankings')}
            className={`flex-1 py-3 px-4 rounded-lg font-medium transition flex items-center justify-center gap-2 ${
              activeTab === 'rankings'
                ? 'bg-blue-500 text-white'
                : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300'
            }`}
          >
            <span>📊</span> رتبه‌بندی جامع
          </button>
          <button
            onClick={() => setActiveTab('leaderboard')}
            className={`flex-1 py-3 px-4 rounded-lg font-medium transition flex items-center justify-center gap-2 ${
              activeTab === 'leaderboard'
                ? 'bg-yellow-500 text-white'
                : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300'
            }`}
          >
            <span>🏆</span> لیدربورد
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`flex-1 py-3 px-4 rounded-lg font-medium transition flex items-center justify-center gap-2 ${
              activeTab === 'history'
                ? 'bg-purple-500 text-white'
                : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300'
            }`}
          >
            <span>📈</span> تاریخچه عملکرد
          </button>
        </div>

        {/* محتوای رتبه‌بندی */}
        {activeTab === 'rankings' && (
          <div className="space-y-6">
            {/* فیلترها */}
            <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow flex items-center gap-4">
              <span className="text-sm text-gray-500">مرتب‌سازی بر اساس:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
              >
                <option value="overall_score">نمره کلی</option>
                <option value="accuracy_score">دقت</option>
                <option value="speed_score">سرعت</option>
                <option value="reliability_score">قابلیت اطمینان</option>
                <option value="total_tasks">تعداد وظایف</option>
              </select>
              <select
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value)}
                className="px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
              >
                <option value="desc">نزولی</option>
                <option value="asc">صعودی</option>
              </select>
            </div>

            {/* لیست مدل‌ها */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow overflow-hidden">
              {loading ? (
                <div className="p-8 text-center text-gray-400">
                  <div className="animate-spin text-4xl mb-2">⏳</div>
                  در حال بارگذاری...
                </div>
              ) : profiles.length === 0 ? (
                <div className="p-8 text-center text-gray-400">
                  <div className="text-5xl mb-4">🤖</div>
                  <p className="text-lg mb-2">هنوز پروفایلی ثبت نشده</p>
                  <p className="text-sm">با اجرای تحلیل سلامت در پروژه‌ها، پروفایل مدل‌ها ایجاد می‌شود</p>
                </div>
              ) : (
                <div className="divide-y dark:divide-gray-700">
                  {profiles.map((profile, idx) => (
                    <div
                      key={profile.model_id}
                      onClick={() => loadProfileDetail(profile.model_id)}
                      className="p-5 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-5">
                          <div className={`w-14 h-14 rounded-xl flex flex-col items-center justify-center font-bold ${
                            idx === 0 ? 'bg-gradient-to-br from-yellow-400 to-amber-500 text-white shadow-lg' :
                            idx === 1 ? 'bg-gradient-to-br from-gray-300 to-gray-400 text-white shadow' :
                            idx === 2 ? 'bg-gradient-to-br from-orange-400 to-orange-500 text-white shadow' :
                            'bg-gray-100 dark:bg-gray-700 text-gray-500'
                          }`}>
                            <span className="text-lg">{idx + 1}</span>
                            {idx < 3 && <span className="text-xs">{getTierBadge(profile.tier)}</span>}
                          </div>
                          <div>
                            <div className="flex items-center gap-3">
                              <span className="text-xl">{getProviderIcon(profile.provider)}</span>
                              <span className="font-bold text-lg">{profile.display_name}</span>
                              <span className={`px-3 py-1 rounded-full text-sm font-bold ${getTierColor(profile.tier)}`}>
                                Tier {profile.tier}
                              </span>
                            </div>
                            <div className="text-sm text-gray-500 mt-1 flex items-center gap-4">
                              <span>{profile.provider}</span>
                              <span>|</span>
                              <span>{profile.total_tasks} وظیفه</span>
                              <span>|</span>
                              <span>{profile.total_analyses} تحلیل</span>
                              {profile.last_activity && (
                                <>
                                  <span>|</span>
                                  <span>آخرین فعالیت: {new Date(profile.last_activity).toLocaleDateString('fa-IR')}</span>
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-8">
                          <div className="grid grid-cols-4 gap-4 text-center">
                            <div>
                              <div className="text-xs text-gray-500 mb-1">دقت</div>
                              <div className="font-bold text-green-500">{profile.accuracy_score}</div>
                            </div>
                            <div>
                              <div className="text-xs text-gray-500 mb-1">سرعت</div>
                              <div className="font-bold text-blue-500">{profile.speed_score}</div>
                            </div>
                            <div>
                              <div className="text-xs text-gray-500 mb-1">کامل‌بودن</div>
                              <div className="font-bold text-purple-500">{profile.completeness_score}</div>
                            </div>
                            <div>
                              <div className="text-xs text-gray-500 mb-1">اطمینان</div>
                              <div className="font-bold text-orange-500">{profile.reliability_score}</div>
                            </div>
                          </div>
                          <div className="border-r pr-6 dark:border-gray-600">
                            <div className="text-xs text-gray-500 mb-1">نمره کل</div>
                            <div className="text-3xl font-bold bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent">
                              {profile.overall_score}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* محتوای لیدربورد */}
        {activeTab === 'leaderboard' && (
          <div className="space-y-6">
            {leaderboard && Object.keys(leaderboard).length > 0 ? (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {Object.entries(leaderboard).map(([key, data]) => (
                  <div
                    key={key}
                    className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg overflow-hidden transform hover:scale-105 transition-transform"
                  >
                    <div className={`p-4 ${
                      key === 'best_accuracy' ? 'bg-gradient-to-r from-green-500 to-emerald-500' :
                      key === 'best_speed' ? 'bg-gradient-to-r from-blue-500 to-cyan-500' :
                      key === 'best_reliability' ? 'bg-gradient-to-r from-purple-500 to-violet-500' :
                      key === 'best_code_quality' ? 'bg-gradient-to-r from-pink-500 to-rose-500' :
                      'bg-gradient-to-r from-orange-500 to-amber-500'
                    }`}>
                      <div className="text-center text-white">
                        <div className="text-4xl mb-2">{getLeaderboardIcon(key)}</div>
                        <div className="font-bold text-lg">{data.label}</div>
                      </div>
                    </div>
                    <div className="p-6 text-center">
                      <div className="text-2xl font-bold mb-1">{data.display_name}</div>
                      <div className={`inline-block px-3 py-1 rounded-full text-sm font-bold mb-3 ${getTierColor(data.tier)}`}>
                        Tier {data.tier}
                      </div>
                      <div className="text-4xl font-bold bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent">
                        {data.score}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-white dark:bg-gray-800 rounded-xl p-8 text-center text-gray-400 shadow">
                <div className="text-5xl mb-4">🏆</div>
                <p className="text-lg">لیدربورد خالی است</p>
                <p className="text-sm mt-2">با اجرای تحلیل‌ها، برترین‌ها مشخص می‌شوند</p>
              </div>
            )}
          </div>
        )}

        {/* محتوای تاریخچه */}
        {activeTab === 'history' && (
          <div className="space-y-6">
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow">
              <h2 className="font-bold text-lg mb-4 flex items-center gap-2">
                <span>📈</span> تاریخچه عملکرد مدل‌ها
              </h2>
              <p className="text-gray-500 mb-4">
                برای مشاهده تاریخچه عملکرد هر مدل، روی آن در تب رتبه‌بندی کلیک کنید.
              </p>
              <div className="bg-gray-100 dark:bg-gray-700 rounded-xl p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {profiles.slice(0, 4).map((profile) => (
                    <div key={profile.model_id} className="bg-white dark:bg-gray-800 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <span className="font-medium">{profile.display_name}</span>
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${getTierColor(profile.tier)}`}>
                          {profile.tier}
                        </span>
                      </div>
                      <div className="space-y-2">
                        <div>
                          <div className="flex justify-between text-xs text-gray-500 mb-1">
                            <span>دقت</span>
                            <span>{profile.accuracy_score}%</span>
                          </div>
                          <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                            <div className="bg-green-500 h-2 rounded-full transition-all" style={{ width: `${profile.accuracy_score}%` }} />
                          </div>
                        </div>
                        <div>
                          <div className="flex justify-between text-xs text-gray-500 mb-1">
                            <span>سرعت</span>
                            <span>{profile.speed_score}%</span>
                          </div>
                          <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                            <div className="bg-blue-500 h-2 rounded-full transition-all" style={{ width: `${profile.speed_score}%` }} />
                          </div>
                        </div>
                        <div>
                          <div className="flex justify-between text-xs text-gray-500 mb-1">
                            <span>کامل‌بودن</span>
                            <span>{profile.completeness_score}%</span>
                          </div>
                          <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                            <div className="bg-purple-500 h-2 rounded-full transition-all" style={{ width: `${profile.completeness_score}%` }} />
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-xl p-4">
              <h4 className="font-medium text-blue-700 dark:text-blue-400 mb-2">💡 نکته درباره نمره‌دهی تجمعی</h4>
              <p className="text-sm text-blue-600 dark:text-blue-400">
                نمرات مدل‌ها تجمعی هستند و بر اساس تمام تحلیل‌های گذشته محاسبه می‌شوند.
                این سیستم به شما کمک می‌کند بهترین مدل را برای پروژه‌های آینده انتخاب کنید.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* مودال جزئیات پروفایل */}
      {selectedProfile && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 overflow-auto">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-auto">
            {detailLoading ? (
              <div className="p-8 text-center">
                <div className="animate-spin text-4xl mb-2">⏳</div>
                در حال بارگذاری...
              </div>
            ) : (
              <>
                <div className="sticky top-0 bg-gradient-to-r from-blue-500 to-purple-600 p-6 text-white">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <span className="text-3xl">{getProviderIcon(selectedProfile.provider)}</span>
                      <div>
                        <h2 className="text-2xl font-bold">{selectedProfile.display_name}</h2>
                        <div className="flex items-center gap-3 mt-1">
                          <span className="text-white/80">{selectedProfile.provider}</span>
                          <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                            selectedProfile.ranking.tier === 'S' ? 'bg-yellow-400 text-yellow-900' :
                            selectedProfile.ranking.tier === 'A' ? 'bg-green-400 text-green-900' :
                            'bg-white/20'
                          }`}>
                            Tier {selectedProfile.ranking.tier} | Rank #{selectedProfile.ranking.rank}
                          </span>
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => setSelectedProfile(null)}
                      className="p-2 hover:bg-white/20 rounded-full transition"
                    >
                      <span className="text-2xl">✕</span>
                    </button>
                  </div>
                </div>
                <div className="p-6 space-y-6">
                  <div>
                    <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
                      <span>📊</span> نمرات تجمعی
                    </h3>
                    <div className="grid grid-cols-3 md:grid-cols-4 gap-4">
                      <div className="text-center p-4 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl text-white">
                        <div className="text-3xl font-bold">{selectedProfile.scores.overall}</div>
                        <div className="text-sm text-white/80">نمره کل</div>
                      </div>
                      <div className="text-center p-4 bg-gray-100 dark:bg-gray-700 rounded-xl">
                        <div className="text-2xl font-bold text-green-500">{selectedProfile.scores.accuracy}</div>
                        <div className="text-xs text-gray-500">دقت</div>
                      </div>
                      <div className="text-center p-4 bg-gray-100 dark:bg-gray-700 rounded-xl">
                        <div className="text-2xl font-bold text-purple-500">{selectedProfile.scores.completeness}</div>
                        <div className="text-xs text-gray-500">کامل‌بودن</div>
                      </div>
                      <div className="text-center p-4 bg-gray-100 dark:bg-gray-700 rounded-xl">
                        <div className="text-2xl font-bold text-orange-500">{selectedProfile.scores.speed}</div>
                        <div className="text-xs text-gray-500">سرعت</div>
                      </div>
                      <div className="text-center p-4 bg-gray-100 dark:bg-gray-700 rounded-xl">
                        <div className="text-2xl font-bold text-cyan-500">{selectedProfile.scores.reliability}</div>
                        <div className="text-xs text-gray-500">قابلیت اطمینان</div>
                      </div>
                      <div className="text-center p-4 bg-gray-100 dark:bg-gray-700 rounded-xl">
                        <div className="text-2xl font-bold text-pink-500">{selectedProfile.scores.code_quality}</div>
                        <div className="text-xs text-gray-500">کیفیت کد</div>
                      </div>
                      <div className="text-center p-4 bg-gray-100 dark:bg-gray-700 rounded-xl">
                        <div className="text-2xl font-bold text-indigo-500">{selectedProfile.scores.reasoning}</div>
                        <div className="text-xs text-gray-500">استدلال</div>
                      </div>
                    </div>
                  </div>
                  <div>
                    <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
                      <span>📈</span> آمار عملکرد
                    </h3>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-xl text-center">
                        <div className="text-2xl font-bold text-green-600">{selectedProfile.stats.correct_findings}</div>
                        <div className="text-sm text-gray-500">یافته‌های درست</div>
                      </div>
                      <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-xl text-center">
                        <div className="text-2xl font-bold text-yellow-600">{selectedProfile.stats.false_positives}</div>
                        <div className="text-sm text-gray-500">False Positive</div>
                      </div>
                      <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-xl text-center">
                        <div className="text-2xl font-bold text-red-600">{selectedProfile.stats.missed_issues}</div>
                        <div className="text-sm text-gray-500">مشکلات کشف نشده</div>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-4 mt-4">
                      <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-lg text-center">
                        <div className="font-bold">{selectedProfile.stats.total_analyses}</div>
                        <div className="text-xs text-gray-500">تحلیل‌ها</div>
                      </div>
                      <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-lg text-center">
                        <div className="font-bold">{selectedProfile.stats.total_tasks}</div>
                        <div className="text-xs text-gray-500">وظایف</div>
                      </div>
                      <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-lg text-center">
                        <div className="font-bold">{selectedProfile.stats.total_debates}</div>
                        <div className="text-xs text-gray-500">مناظرات</div>
                      </div>
                    </div>
                  </div>
                  <div>
                    <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
                      <span>⚡</span> کارایی
                    </h3>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-lg text-center">
                        <div className="font-bold">{selectedProfile.performance.avg_response_time}ms</div>
                        <div className="text-xs text-gray-500">میانگین زمان پاسخ</div>
                      </div>
                      <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-lg text-center">
                        <div className="font-bold">{selectedProfile.performance.total_tokens_used.toLocaleString()}</div>
                        <div className="text-xs text-gray-500">توکن مصرفی</div>
                      </div>
                      <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-lg text-center">
                        <div className="font-bold">${selectedProfile.performance.total_cost.toFixed(4)}</div>
                        <div className="text-xs text-gray-500">هزینه کل</div>
                      </div>
                    </div>
                  </div>
                  <div className="grid md:grid-cols-2 gap-6">
                    <div>
                      <h3 className="font-bold mb-3 text-green-600 flex items-center gap-2">
                        <span>💪</span> نقاط قوت
                      </h3>
                      <ul className="space-y-2">
                        {selectedProfile.capabilities.strengths.length > 0 ? (
                          selectedProfile.capabilities.strengths.map((s, i) => (
                            <li key={i} className="flex items-center gap-2 text-sm">
                              <span className="text-green-500">✓</span>
                              <span>{s}</span>
                            </li>
                          ))
                        ) : (
                          <li className="text-gray-400 text-sm">هنوز شناسایی نشده</li>
                        )}
                      </ul>
                    </div>
                    <div>
                      <h3 className="font-bold mb-3 text-red-600 flex items-center gap-2">
                        <span>⚠️</span> نقاط ضعف
                      </h3>
                      <ul className="space-y-2">
                        {selectedProfile.capabilities.weaknesses.length > 0 ? (
                          selectedProfile.capabilities.weaknesses.map((w, i) => (
                            <li key={i} className="flex items-center gap-2 text-sm">
                              <span className="text-red-500">✗</span>
                              <span>{w}</span>
                            </li>
                          ))
                        ) : (
                          <li className="text-gray-400 text-sm">هنوز شناسایی نشده</li>
                        )}
                      </ul>
                    </div>
                  </div>
                  {selectedProfile.validation_history && selectedProfile.validation_history.length > 0 && (
                    <div>
                      <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
                        <span>📋</span> تاریخچه اعتبارسنجی (۲۰ مورد اخیر)
                      </h3>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead className="bg-gray-100 dark:bg-gray-700">
                            <tr>
                              <th className="p-2 text-right">نوع</th>
                              <th className="p-2 text-center">Precision</th>
                              <th className="p-2 text-center">Recall</th>
                              <th className="p-2 text-center">F1</th>
                              <th className="p-2 text-center">زمان</th>
                              <th className="p-2 text-left">تاریخ</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y dark:divide-gray-700">
                            {selectedProfile.validation_history.map((v: any, idx: number) => (
                              <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                                <td className="p-2">{v.task_type}</td>
                                <td className="p-2 text-center font-medium text-green-500">{v.precision}%</td>
                                <td className="p-2 text-center font-medium text-blue-500">{v.recall}%</td>
                                <td className="p-2 text-center font-medium text-purple-500">{v.f1_score}%</td>
                                <td className="p-2 text-center">{v.response_time}ms</td>
                                <td className="p-2 text-left text-gray-500">
                                  {v.created_at ? new Date(v.created_at).toLocaleDateString('fa-IR') : '-'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                  <div className="text-xs text-gray-500 flex justify-between border-t dark:border-gray-700 pt-4">
                    <span>ایجاد: {selectedProfile.timestamps.created_at ? new Date(selectedProfile.timestamps.created_at).toLocaleString('fa-IR') : '-'}</span>
                    <span>آخرین فعالیت: {selectedProfile.timestamps.last_activity ? new Date(selectedProfile.timestamps.last_activity).toLocaleString('fa-IR') : '-'}</span>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
