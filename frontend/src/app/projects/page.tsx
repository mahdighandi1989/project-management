'use client';

/**
 * «پروژه‌ها و نمودارها» — owner, 2026-11-15 (plan item 3): the two pages work on the same
 * projects, so they live under one page. Their code is unchanged and lives in
 * `components/views/ProjectsView.tsx` and `components/views/DiagramsView.tsx`; this page
 * only switches between them with `?view=diagrams` (components/ViewHub.tsx). The old
 * `/diagrams` address redirects here, and `/projects?id=…` keeps working.
 */

import ViewHub from '@/components/ViewHub';
import ProjectsView from '@/components/views/ProjectsView';
import DiagramsView from '@/components/views/DiagramsView';

export default function ProjectsPage() {
  return (
    <ViewHub section="projects-hub" views={[
      { id: 'projects', label: 'پروژه‌ها', emoji: '📁', render: () => <ProjectsView /> },
      { id: 'diagrams', label: 'نمودارها', emoji: '📊', render: () => <DiagramsView /> },
    ]} />
  );
}
