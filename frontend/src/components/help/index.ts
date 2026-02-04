/**
 * سیستم راهنمای جامع
 *
 * این ماژول شامل کامپوننت‌ها و ابزارهای لازم برای نمایش راهنما در هر صفحه است:
 *
 * - HelpSystem: دکمه شناور و پنل راهنمای اصلی
 * - HelpProvider: Context و Provider برای سیستم tooltip
 * - HelpTooltip: کامپوننت tooltip ساده
 * - helpData: داده‌های راهنما برای هر صفحه
 */

// کامپوننت اصلی سیستم راهنما
export { default as HelpSystem } from './HelpSystem';

// Provider و hooks
export { HelpProvider, useHelp, WithHelpTooltip, SimpleTooltip } from './HelpProvider';

// کامپوننت tooltip
export { default as HelpTooltip } from './HelpTooltip';

// داده‌ها و توابع کمکی
export {
  type PageHelp,
  type ElementHelp,
  getPageHelp,
  getElementHelp,
  allPagesHelp,
  dashboardHelp,
  projectsHelp,
  projectDetailHelp,
  debateHelp,
  modelsHelp,
  settingsHelp,
  creatorHelp,
} from './helpData';
