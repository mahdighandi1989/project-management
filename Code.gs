// ╔═══════════════════════════════════════════════════════════════════════════════╗
// ║  سیستم مناظره و همکاری هوش مصنوعی + سیستم مدیریت پروژه پایدار                ║
// ║  نسخه: 17.0 THINK TANK - اتاق فکر مهندسی هوشمند (کامل)                        ║
// ╠═══════════════════════════════════════════════════════════════════════════════╣
// ║  ✅ همه قابلیت‌های v16 (Debate, Projects, Models, etc)                        ║
// ║  ✅ 🧠 PHASE 1: SMART ENGINEERING THINK TANK                                   ║
// ║     - تحلیل پروژه‌های خارجی (Google Console, GitHub, etc)                     ║
// ║     - تولید خودکار نمودار Mermaid (معماری، جریان داده، کامپوننت)              ║
// ║     - دستورات اجرایی گام‌به‌گام با قالب استاندارد                             ║
// ║     - مکانیزم بازخورد از اجرای دستورات                                        ║
// ║  ✅ 🗺️ PHASE 2: DYNAMIC ROADMAP SYSTEM                                         ║
// ║     - نقشه راه داینامیک با وابستگی تسک‌ها                                     ║
// ║     - Milestones و KPIs قابل اندازه‌گیری                                      ║
// ║     - نمودار Gantt و Critical Path                                            ║
// ║     - تشخیص انحراف و هشدار                                                     ║
// ║  ✅ 🧠 PHASE 3: INCREMENTAL LEARNING SYSTEM                                    ║
// ║     - پایگاه دانش پروژه‌محور (Knowledge Base)                                 ║
// ║     - استخراج الگوها و Anti-Patterns                                          ║
// ║     - یادگیری از آموزش کاربر                                                   ║
// ║     - ارزیابی کد بر اساس معیارهای استاندارد                                   ║
// ║     - پیشنهادات هوشمند و قالب‌های تطبیقی                                      ║
// ║  ✅ 🚀 PERSISTENT PROJECT SYSTEM - سیستم مدیریت پروژه پایدار                  ║
// ║  ✅ Model Registry داینامیک + OpenRouter + Groq                               ║
// ║  ✅ Smart Model Selection + Auto Fallback (3-level)                           ║
// ║  ✅ 🔗 COMPATIBILITY LAYER - لایه سازگاری کامل با Frontend                    ║
// ╚═══════════════════════════════════════════════════════════════════════════════╝

// ========================================
// 0. WEB FETCHING - استخراج محتوای لینک‌ها
// ========================================

/**
 * استخراج محتوای یک URL
 * @param {string} url - آدرس وب
 * @returns {object} - محتوای استخراج شده
 */
function fetchUrlContent(url) {
  try {
    Logger.log('🌐 Fetching URL: ' + url);
    
    // اعتبارسنجی URL
    if (!url || !url.startsWith('http')) {
      return { success: false, error: 'URL نامعتبر است' };
    }
    
    // لیست سایت‌هایی که SPA هستن و قابل fetch نیستن
    const spaBlockedDomains = [
      'claude.ai',
      'chat.openai.com', 
      'chatgpt.com',
      'gemini.google.com',
      'poe.com',
      'perplexity.ai',
      'you.com'
    ];
    
    // بررسی آیا URL مربوط به SPA است
    const urlLower = url.toLowerCase();
    for (const domain of spaBlockedDomains) {
      if (urlLower.includes(domain)) {
        Logger.log('  ⚠️ SPA site detected: ' + domain);
        return {
          success: false,
          url: url,
          isSPA: true,
          error: `سایت ${domain} یک Single Page Application است و محتوای آن به صورت داینامیک با JavaScript لود می‌شود. لطفاً محتوای مورد نظر را مستقیماً کپی کنید.`,
          suggestion: 'محتوای صفحه را کپی کرده و در اینجا قرار دهید'
        };
      }
    }
    
    // تنظیمات درخواست
    const options = {
      method: 'get',
      muteHttpExceptions: true,
      followRedirects: true,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,fa;q=0.8',
        'Cache-Control': 'no-cache'
      }
    };
    
    const response = UrlFetchApp.fetch(url, options);
    const responseCode = response.getResponseCode();
    
    Logger.log('  📡 Response code: ' + responseCode);
    
    if (responseCode !== 200) {
      return { 
        success: false, 
        error: `خطای HTTP: ${responseCode}`,
        code: responseCode
      };
    }
    
    const contentType = response.getHeaders()['Content-Type'] || '';
    const rawContent = response.getContentText();
    
    Logger.log('  📄 Content type: ' + contentType);
    Logger.log('  📏 Raw content length: ' + rawContent.length);
    
    // پردازش بر اساس نوع محتوا
    let extractedText = '';
    let title = '';
    
    if (contentType.includes('text/html')) {
      // استخراج متن از HTML
      extractedText = extractTextFromHtml(rawContent);
      
      // استخراج عنوان
      const titleMatch = rawContent.match(/<title[^>]*>(.*?)<\/title>/i);
      title = titleMatch ? titleMatch[1].trim() : url;
      
      // بررسی آیا محتوا خیلی کم است (احتمالاً SPA)
      if (extractedText.length < 500) {
        Logger.log('  ⚠️ Content too short, might be SPA');
        
        // بررسی نشانه‌های SPA
        const spaIndicators = ['__NEXT_DATA__', 'react-root', 'app-root', 'ng-app', 'data-reactroot'];
        const isSPA = spaIndicators.some(indicator => rawContent.includes(indicator));
        
        if (isSPA) {
          return {
            success: false,
            url: url,
            isSPA: true,
            error: 'این صفحه یک Single Page Application است و محتوای آن با JavaScript لود می‌شود.',
            suggestion: 'لطفاً محتوای صفحه را مستقیماً کپی کرده و در پرامپت قرار دهید.'
          };
        }
      }
      
    } else if (contentType.includes('application/json')) {
      try {
        const jsonData = JSON.parse(rawContent);
        extractedText = JSON.stringify(jsonData, null, 2);
        title = 'JSON Data';
      } catch (e) {
        extractedText = rawContent;
      }
      
    } else if (contentType.includes('text/plain') || contentType.includes('text/markdown')) {
      extractedText = rawContent;
      title = 'Text Content';
      
    } else {
      extractedText = rawContent.substring(0, 50000);
      title = 'Content from ' + url;
    }
    
    // اگه محتوا خیلی کم بود، warning بده
    if (extractedText.length < 200) {
      Logger.log('  ⚠️ Very short content extracted');
      return {
        success: false,
        url: url,
        error: 'محتوای قابل استخراج از این صفحه بسیار کم است. احتمالاً صفحه نیاز به JavaScript دارد.',
        suggestion: 'لطفاً محتوای صفحه را مستقیماً کپی کنید.'
      };
    }
    
    Logger.log('  ✅ Content extracted: ' + extractedText.length + ' chars');
    
    return {
      success: true,
      url: url,
      title: title,
      content: extractedText.substring(0, 100000),
      contentType: contentType,
      length: extractedText.length,
      fetchedAt: new Date().toISOString()
    };
    
  } catch (error) {
    Logger.log('❌ URL Fetch Error: ' + error);
    return {
      success: false,
      url: url,
      error: error.message || 'خطا در دریافت محتوا'
    };
  }
}

/**
 * استخراج متن خالص از HTML
 */
function extractTextFromHtml(html) {
  try {
    // حذف script و style
    let text = html.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '');
    text = text.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
    text = text.replace(/<noscript[^>]*>[\s\S]*?<\/noscript>/gi, '');
    
    // حذف کامنت‌ها
    text = text.replace(/<!--[\s\S]*?-->/g, '');
    
    // تبدیل برخی تگ‌ها به newline
    text = text.replace(/<br\s*\/?>/gi, '\n');
    text = text.replace(/<\/p>/gi, '\n\n');
    text = text.replace(/<\/div>/gi, '\n');
    text = text.replace(/<\/li>/gi, '\n');
    text = text.replace(/<\/h[1-6]>/gi, '\n\n');
    
    // حذف همه تگ‌های HTML
    text = text.replace(/<[^>]+>/g, ' ');
    
    // تبدیل HTML entities
    text = text.replace(/&nbsp;/g, ' ');
    text = text.replace(/&amp;/g, '&');
    text = text.replace(/&lt;/g, '<');
    text = text.replace(/&gt;/g, '>');
    text = text.replace(/&quot;/g, '"');
    text = text.replace(/&#39;/g, "'");
    
    // پاکسازی فاصله‌های اضافی
    text = text.replace(/\s+/g, ' ');
    text = text.replace(/\n\s+\n/g, '\n\n');
    text = text.replace(/\n{3,}/g, '\n\n');
    
    return text.trim();
  } catch (e) {
    return html.replace(/<[^>]+>/g, ' ').trim();
  }
}

/**
 * پردازش چندین URL
 */
function fetchMultipleUrls(urls) {
  const results = [];
  
  for (const url of urls) {
    const result = fetchUrlContent(url);
    results.push(result);
    
    // تأخیر کوتاه برای جلوگیری از rate limiting
    Utilities.sleep(500);
  }
  
  return results;
}

/**
 * تشخیص URL در متن
 */
function extractUrlsFromText(text) {
  const urlPattern = /https?:\/\/[^\s<>"{}|\\^`\[\]]+/g;
  const matches = text.match(urlPattern) || [];
  return [...new Set(matches)]; // حذف تکراری‌ها
}

// ========================================
// 1. MODEL REGISTRY - سیستم داینامیک مدیریت مدل‌ها
// ========================================

/**
 * دریافت لیست مدل‌های موجود از API ها (داینامیک)
 * توجه: این تابع فقط برای نمایش استفاده میشه، نه برای اضافه کردن به Registry
 */
function discoverAvailableModels() {
  const discoveredModels = [];
  const props = PropertiesService.getScriptProperties();
  
  // 1. OpenAI Models
  try {
    const openaiKey = props.getProperty('OPENAI_API_KEY');
    if (openaiKey) {
      const response = UrlFetchApp.fetch('https://api.openai.com/v1/models', {
        method: 'get',
        headers: { 'Authorization': 'Bearer ' + openaiKey },
        muteHttpExceptions: true
      });
      
      if (response.getResponseCode() === 200) {
        const data = JSON.parse(response.getContentText());
        data.data.forEach(model => {
          if (model.id.includes('gpt-4') || model.id.includes('gpt-3.5')) {
            discoveredModels.push({
              id: model.id,
              provider: 'openai',
              name: model.id,
              discovered: true
            });
          }
        });
        Logger.log('✅ OpenAI: ' + discoveredModels.filter(m => m.provider === 'openai').length + ' models');
      }
    }
  } catch (e) {
    Logger.log('⚠️ OpenAI discovery failed: ' + e);
  }
  
  // 2. Google/Gemini Models
  try {
    const geminiKey = props.getProperty('GEMINI_API_KEY');
    if (geminiKey) {
      const response = UrlFetchApp.fetch(
        'https://generativelanguage.googleapis.com/v1beta/models?key=' + geminiKey,
        { muteHttpExceptions: true }
      );
      
      if (response.getResponseCode() === 200) {
        const data = JSON.parse(response.getContentText());
        if (data.models) {
          data.models.forEach(model => {
            const modelId = model.name.replace('models/', '');
            // فقط مدل‌های generateContent
            if (model.supportedGenerationMethods && 
                model.supportedGenerationMethods.includes('generateContent')) {
              discoveredModels.push({
                id: modelId,
                provider: 'gemini',
                name: model.displayName || modelId,
                discovered: true
              });
            }
          });
          Logger.log('✅ Gemini: ' + discoveredModels.filter(m => m.provider === 'gemini').length + ' models');
        }
      }
    }
  } catch (e) {
    Logger.log('⚠️ Gemini discovery failed: ' + e);
  }
  
  return discoveredModels;
}

/**
 * آپدیت MODEL_REGISTRY با مدل‌های جدید - غیرفعال برای جلوگیری از خطا
 * این تابع فعلاً فقط لاگ میکنه و تغییری نمیده
 */
function updateModelRegistry() {
  try {
    const discovered = discoverAvailableModels();
    Logger.log('🔍 Discovered ' + discovered.length + ' models from APIs');
    
    // فقط لاگ کن، تغییری نده
    const newModels = discovered.filter(m => !MODEL_REGISTRY[m.id]);
    if (newModels.length > 0) {
      Logger.log('🆕 New models found (not added): ' + newModels.map(m => m.id).join(', '));
    }
    
    return { 
      success: true,
      discovered: discovered.length, 
      newModels: newModels.map(m => m.id)
    };
  } catch (e) {
    Logger.log('❌ updateModelRegistry error: ' + e);
    return { success: false, error: e.message };
  }
}

function getProviderEndpoint(provider) {
  const endpoints = {
    'openai': 'https://api.openai.com/v1/chat/completions',
    'claude': 'https://api.anthropic.com/v1/messages',
    'gemini': 'https://generativelanguage.googleapis.com/v1beta/models/',
    'deepseek': 'https://api.deepseek.com/chat/completions'
  };
  return endpoints[provider] || '';
}

const MODEL_REGISTRY = {
  // OpenAI Models
  'gpt-4-turbo': {
    provider: 'openai',
    name: 'GPT-4 Turbo',
    endpoint: 'https://api.openai.com/v1/chat/completions',
    capabilities: ['text', 'code', 'reasoning', 'long-context'],
    maxTokens: 4096,
    contextWindow: 128000,
    strengths: ['reasoning', 'code', 'complex-tasks'],
    weaknesses: ['image-generation'],
    costPer1kTokens: 0.01,
    priority: 1,
    enabled: true
  },
  
  'gpt-4': {
    provider: 'openai',
    name: 'GPT-4',
    endpoint: 'https://api.openai.com/v1/chat/completions',
    capabilities: ['text', 'code', 'reasoning'],
    maxTokens: 4096,
    contextWindow: 8192,
    strengths: ['reasoning', 'accuracy'],
    weaknesses: ['speed', 'long-context'],
    costPer1kTokens: 0.03,
    priority: 2,
    enabled: true
  },
  
  'gpt-3.5-turbo': {
    provider: 'openai',
    name: 'GPT-3.5 Turbo',
    endpoint: 'https://api.openai.com/v1/chat/completions',
    capabilities: ['text', 'code', 'fast-response'],
    maxTokens: 4096,
    contextWindow: 16385,
    strengths: ['speed', 'cost-effective'],
    weaknesses: ['complex-reasoning'],
    costPer1kTokens: 0.0015,
    priority: 3,
    enabled: true
  },
  
  'gpt-4o': {
    provider: 'openai',
    name: 'GPT-4o',
    endpoint: 'https://api.openai.com/v1/chat/completions',
    capabilities: ['text', 'image-analysis', 'vision', 'code', 'reasoning'],
    maxTokens: 4096,
    contextWindow: 128000,
    strengths: ['image-analysis', 'multimodal', 'reasoning'],
    weaknesses: ['cost'],
    costPer1kTokens: 0.005,
    priority: 1,
    enabled: true,
    supportsImages: true
  },
  
  'gpt-4o-mini': {
    provider: 'openai',
    name: 'GPT-4o Mini',
    endpoint: 'https://api.openai.com/v1/chat/completions',
    capabilities: ['text', 'image-analysis', 'fast-response'],
    maxTokens: 4096,
    contextWindow: 128000,
    strengths: ['speed', 'cost-effective', 'multimodal'],
    weaknesses: ['complex-reasoning'],
    costPer1kTokens: 0.00015,
    priority: 2,
    enabled: true,
    supportsImages: true
  },
  
  // Claude Models (Updated December 2024)
  'claude-sonnet-4-20250514': {
    provider: 'claude',
    name: 'Claude Sonnet 4',
    endpoint: 'https://api.anthropic.com/v1/messages',
    capabilities: ['text', 'code', 'reasoning', 'long-context'],
    maxTokens: 4096,
    contextWindow: 200000,
    strengths: ['reasoning', 'long-context', 'accuracy', 'latest'],
    weaknesses: ['cost'],
    costPer1kTokens: 0.003,
    priority: 1,
    enabled: true
  },
  
  'claude-3-5-sonnet-20241022': {
    provider: 'claude',
    name: 'Claude 3.5 Sonnet',
    endpoint: 'https://api.anthropic.com/v1/messages',
    capabilities: ['text', 'code', 'reasoning', 'long-context'],
    maxTokens: 4096,
    contextWindow: 200000,
    strengths: ['reasoning', 'accuracy', 'balance'],
    weaknesses: [],
    costPer1kTokens: 0.003,
    priority: 2,
    enabled: true
  },
  
  'claude-3-haiku-20240307': {
    provider: 'claude',
    name: 'Claude 3 Haiku',
    endpoint: 'https://api.anthropic.com/v1/messages',
    capabilities: ['text', 'fast-response'],
    maxTokens: 4096,
    contextWindow: 200000,
    strengths: ['speed', 'cost-effective'],
    weaknesses: ['complex-reasoning'],
    costPer1kTokens: 0.00025,
    priority: 3,
    enabled: true
  },
  
  // DeepSeek Models
  'deepseek-chat': {
    provider: 'deepseek',
    name: 'DeepSeek Chat',
    endpoint: 'https://api.deepseek.com/chat/completions',
    capabilities: ['text', 'code', 'reasoning'],
    maxTokens: 4096,
    contextWindow: 32000,
    strengths: ['code', 'reasoning', 'cost-effective'],
    weaknesses: ['multimodal'],
    costPer1kTokens: 0.0014,
    priority: 2,
    enabled: true
  },
  
  'deepseek-coder': {
    provider: 'deepseek',
    name: 'DeepSeek Coder',
    endpoint: 'https://api.deepseek.com/chat/completions',
    capabilities: ['code', 'text'],
    maxTokens: 4096,
    contextWindow: 16000,
    strengths: ['code', 'programming'],
    weaknesses: ['general-text'],
    costPer1kTokens: 0.0014,
    priority: 1,
    enabled: true
  },
  
  // ✅ v16.0: DeepSeek Reasoner - مدل استدلال جدید
  'deepseek-reasoner': {
    provider: 'deepseek',
    name: 'DeepSeek Reasoner',
    endpoint: 'https://api.deepseek.com/chat/completions',
    capabilities: ['reasoning', 'code', 'analysis', 'math'],
    maxTokens: 8192,
    contextWindow: 64000,
    strengths: ['reasoning', 'math', 'logic', 'physics'],
    weaknesses: ['speed', 'cost'],
    costPer1kTokens: 0.0055,
    priority: 1,
    enabled: true
  },
  
  // Gemini Models
  // ✅ v17.2: مدل‌های جدید Gemini (آپدیت شده)
  'gemini-2.5-pro': {
    provider: 'gemini',
    name: 'Gemini 2.5 Pro',
    endpoint: 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent',
    capabilities: ['text', 'code', 'image-analysis', 'video-analysis', 'long-context', 'thinking'],
    maxTokens: 65536,
    contextWindow: 1048576,
    strengths: ['long-context', 'multimodal', 'video', 'reasoning', 'thinking'],
    weaknesses: [],
    costPer1kTokens: 0.00125,
    priority: 1,
    enabled: true,
    supportsImages: true,
    supportsVideo: true
  },
  
  'gemini-2.5-flash': {
    provider: 'gemini',
    name: 'Gemini 2.5 Flash',
    endpoint: 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent',
    capabilities: ['text', 'fast-response', 'image-analysis', 'video-analysis', 'thinking'],
    maxTokens: 65536,
    contextWindow: 1048576,
    strengths: ['speed', 'cost-effective', 'video', 'thinking'],
    weaknesses: [],
    costPer1kTokens: 0.00015,
    priority: 2,
    enabled: true,
    supportsImages: true,
    supportsVideo: true
  },
  
  'gemini-2.0-flash': {
    provider: 'gemini',
    name: 'Gemini 2.0 Flash',
    endpoint: 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent',
    capabilities: ['text', 'fast-response', 'image-analysis', 'video-analysis'],
    maxTokens: 8192,
    contextWindow: 1048576,
    strengths: ['speed', 'cost-effective', 'video'],
    weaknesses: [],
    costPer1kTokens: 0.00001,
    priority: 3,
    enabled: true,
    supportsImages: true,
    supportsVideo: true
  },
  
  // مدل‌های تولید تصویر
  'gemini-2.0-flash-preview-image-generation': {
    provider: 'gemini',
    name: 'Gemini 2.0 Flash (Image Gen)',
    endpoint: 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-preview-image-generation:generateContent',
    capabilities: ['image-generation', 'text'],
    maxTokens: 8192,
    contextWindow: 32000,
    strengths: ['image-generation', 'creative'],
    weaknesses: ['experimental'],
    costPer1kTokens: 0.0001,
    priority: 1,
    enabled: true,
    supportsImages: true,
    isImageGenerator: true
  },
  
  'imagen-3': {
    provider: 'gemini',
    name: 'Imagen 3',
    endpoint: 'https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict',
    capabilities: ['image-generation'],
    maxTokens: 0,
    contextWindow: 0,
    strengths: ['high-quality-images', 'photorealistic'],
    weaknesses: ['only-images'],
    costPer1kTokens: 0.04,
    priority: 2,
    enabled: true,
    supportsImages: false,
    isImageGenerator: true
  },
  
  'dall-e-3': {
    provider: 'openai',
    name: 'DALL-E 3',
    endpoint: 'https://api.openai.com/v1/images/generations',
    capabilities: ['image-generation'],
    maxTokens: 0,
    contextWindow: 4000,
    strengths: ['creative-images', 'artistic', 'prompt-understanding', 'text-in-images'],
    weaknesses: ['only-images', 'cost'],
    costPer1kTokens: 0,
    costPerImage: 0.04, // standard quality
    priority: 1,
    enabled: true,
    supportsImages: false,
    isImageGenerator: true
  }
};

// Alias های سازگاری با نام‌های قدیمی
const MODEL_ALIASES = {
  'gpt4': 'gpt-4o',
  'gpt-4': 'gpt-4-turbo',
  'gpt-4-vision': 'gpt-4o',
  'gpt-4-vision-preview': 'gpt-4o',
  'claude': 'claude-sonnet-4-20250514',
  'claude-3': 'claude-3-5-sonnet-20241022',
  'claude-3-opus': 'claude-sonnet-4-20250514',
  'claude-3-opus-20240229': 'claude-sonnet-4-20250514',
  'claude-3-sonnet': 'claude-3-5-sonnet-20241022',
  'claude-3-sonnet-20240229': 'claude-3-5-sonnet-20241022',
  'deepseek': 'deepseek-chat',
  'gemini': 'gemini-2.0-flash'
};

// ========================================
// 2. CONFIGURATION - با امنیت بهبود یافته
// ========================================

const CONFIG = {
  // شناسه‌ها
  sheetId: '1srIuati7__9gsbIDS8xeh77lBOPUHD6pyPLGUY3hn3c',
  docId: '1FoibmBwWHLJ-Q4p1JWZ8oiM7Ko8-K2Pu6dLXUh_6XXo',
  folderId: '1QXdJClgvfTDB_aggrPNKA1HRe7jmFYci',
  outputFolderId: '1QXdJClgvfTDB_aggrPNKA1HRe7jmFYci',
  generatedFilesFolderId: '1QXdJClgvfTDB_aggrPNKA1HRe7jmFYci', // پوشه فایل‌های تولیدی
  
  // ✅ v17.2: افزایش توکن برای پاسخ‌های باکیفیت‌تر
  maxTokensPerModel: 4000,        // ✅ افزایش از 2000 به 4000
  maxTokensForScoring: 1000,      // ✅ افزایش از 500 به 1000
  maxTokensForJudge: 2000,        // ✅ افزایش از 1000 به 2000
  maxTokensForSummary: 2500,      // ✅ افزایش از 1500 به 2500
  
  // 🔥 تنظیمات timeout - Google limit = 360 ثانیه (6 دقیقه)
  pauseThreshold: 150,     // 🔥 2.5 دقیقه - زودتر pause کن!
  maxModelTime: 60,        // ✅ افزایش از 45 به 60 ثانیه برای هر مدل  
  safetyMargin: 20,        // 20 ثانیه حاشیه امن
  pauseAfterEachModel: true,  // 🔥 فعال - بعد از هر مدل pause کن!
  
  checkInterval: 30,
  maxPromptLength: 100000  // ✅ افزایش از 80K به 100K برای محتوای بیشتر
};

// ========================================
// 📁 FILE TYPE DEFINITIONS - تعریف انواع فایل
// ========================================

const FILE_CATEGORIES = {
  // تصاویر
  images: {
    extensions: ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg', 'tiff', 'tif', 'ico', 'heic', 'heif', 'avif', 'raw', 'cr2', 'nef', 'arw'],
    mimeTypes: ['image/'],
    requiresVision: true,
    icon: '🖼️',
    description: 'فایل تصویری'
  },
  
  // ویدیو
  videos: {
    extensions: ['mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm', 'm4v', '3gp'],
    mimeTypes: ['video/'],
    requiresVision: true,
    extractable: false,
    icon: '🎬',
    description: 'فایل ویدیویی'
  },
  
  // صوت
  audio: {
    extensions: ['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a', 'wma', 'opus'],
    mimeTypes: ['audio/'],
    requiresTranscription: true,
    icon: '🎵',
    description: 'فایل صوتی'
  },
  
  // PDF
  pdf: {
    extensions: ['pdf'],
    mimeTypes: ['application/pdf'],
    extractable: true,
    ocrSupported: true,
    icon: '📕',
    description: 'سند PDF'
  },
  
  // اسناد متنی
  documents: {
    extensions: ['txt', 'rtf', 'odt', 'pages'],
    mimeTypes: ['text/plain', 'text/rtf', 'application/rtf'],
    extractable: true,
    icon: '📄',
    description: 'سند متنی'
  },
  
  // Word
  word: {
    extensions: ['doc', 'docx', 'docm'],
    mimeTypes: ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml'],
    extractable: true,
    convertToGoogleDoc: true,
    icon: '📝',
    description: 'سند Word'
  },
  
  // Excel
  spreadsheet: {
    extensions: ['xls', 'xlsx', 'xlsm', 'xlsb', 'ods', 'numbers'],
    mimeTypes: ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml'],
    extractable: true,
    convertToGoogleSheet: true,
    icon: '📊',
    description: 'صفحه گسترده'
  },
  
  // PowerPoint
  presentation: {
    extensions: ['ppt', 'pptx', 'pptm', 'odp', 'key'],
    mimeTypes: ['application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml'],
    extractable: true,
    convertToGoogleSlides: true,
    icon: '📽️',
    description: 'ارائه'
  },
  
  // داده‌های ساختاریافته
  data: {
    extensions: ['csv', 'tsv', 'json', 'jsonl', 'ndjson', 'xml', 'yaml', 'yml', 'toml', 'ini', 'conf', 'cfg'],
    mimeTypes: ['application/json', 'text/csv', 'application/xml', 'text/xml'],
    extractable: true,
    structured: true,
    icon: '📋',
    description: 'داده ساختاریافته'
  },
  
  // کد برنامه‌نویسی
  code: {
    extensions: [
      // Web
      'html', 'htm', 'css', 'scss', 'sass', 'less', 'js', 'jsx', 'ts', 'tsx', 'vue', 'svelte',
      // Backend
      'py', 'rb', 'php', 'java', 'kt', 'kts', 'scala', 'groovy', 'go', 'rs', 'swift', 'dart',
      // Systems
      'c', 'cpp', 'cc', 'cxx', 'h', 'hpp', 'cs', 'fs', 'vb', 'asm', 's',
      // Scripting
      'sh', 'bash', 'zsh', 'fish', 'ps1', 'psm1', 'bat', 'cmd', 'lua', 'perl', 'pl', 'tcl',
      // Google Apps Script
      'gs', 'gas',
      // Data Science
      'r', 'rmd', 'jl', 'ipynb', 'm', 'matlab',
      // Database
      'sql', 'plsql', 'tsql', 'pgsql',
      // Config/Build
      'makefile', 'cmake', 'gradle', 'dockerfile', 'vagrantfile',
      // Other
      'zig', 'nim', 'v', 'crystal', 'elixir', 'ex', 'exs', 'erl', 'hrl', 'clj', 'cljs', 'lisp', 'scm', 'hs', 'ml', 'mli', 'f90', 'f95', 'for', 'pas', 'pp', 'ada', 'adb', 'ads', 'cob', 'cbl', 'pro', 'pl'
    ],
    mimeTypes: ['text/x-', 'application/x-', 'text/javascript', 'application/javascript'],
    extractable: true,
    requiresCodeAnalysis: true,
    icon: '💻',
    description: 'کد برنامه‌نویسی'
  },
  
  // Markdown و مستندات
  markdown: {
    extensions: ['md', 'markdown', 'mdown', 'mkd', 'rst', 'adoc', 'asciidoc', 'org', 'tex', 'latex'],
    mimeTypes: ['text/markdown', 'text/x-markdown'],
    extractable: true,
    icon: '📑',
    description: 'مستند Markdown'
  },
  
  // فایل‌های آرشیو
  archive: {
    extensions: ['zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz', 'tgz', 'tbz2', 'lz', 'lzma', 'cab', 'iso', 'dmg'],
    mimeTypes: ['application/zip', 'application/x-rar', 'application/x-7z-compressed'],
    extractable: false,
    icon: '📦',
    description: 'فایل فشرده'
  },
  
  // فونت
  font: {
    extensions: ['ttf', 'otf', 'woff', 'woff2', 'eot', 'fon'],
    mimeTypes: ['font/', 'application/font'],
    extractable: false,
    icon: '🔤',
    description: 'فایل فونت'
  },
  
  // eBook
  ebook: {
    extensions: ['epub', 'mobi', 'azw', 'azw3', 'fb2', 'djvu'],
    mimeTypes: ['application/epub'],
    extractable: true,
    icon: '📚',
    description: 'کتاب الکترونیکی'
  },
  
  // CAD و 3D
  cad3d: {
    extensions: ['dwg', 'dxf', 'stl', 'obj', 'fbx', 'blend', 'max', '3ds', 'skp', 'step', 'stp', 'iges', 'igs'],
    mimeTypes: [],
    extractable: false,
    requiresSpecialized: true,
    icon: '🏗️',
    description: 'فایل CAD/3D'
  },
  
  // فایل‌های برنامه
  executable: {
    extensions: ['exe', 'msi', 'app', 'apk', 'ipa', 'deb', 'rpm', 'pkg', 'jar', 'war', 'ear'],
    mimeTypes: ['application/x-executable', 'application/x-msdownload'],
    extractable: false,
    dangerous: true,
    icon: '⚙️',
    description: 'فایل اجرایی'
  }
};

// قابلیت‌های مورد نیاز برای هر نوع فایل
const FILE_CAPABILITIES = {
  vision: ['images', 'videos', 'pdf'],
  code: ['code'],
  data: ['data', 'spreadsheet'],
  document: ['documents', 'word', 'pdf', 'markdown', 'ebook'],
  presentation: ['presentation'],
  audio: ['audio']
};

// مدل‌های مناسب برای هر قابلیت
const CAPABILITY_MODELS = {
  vision: {
    primary: ['gpt-4o', 'claude-sonnet-4-20250514', 'gemini-2.0-flash'],
    fallback: ['gpt-4o-mini', 'claude-3-5-sonnet-20241022', 'gemini-2.5-flash']
  },
  code: {
    primary: ['deepseek-coder', 'gpt-4o', 'claude-sonnet-4-20250514'],
    fallback: ['deepseek-chat', 'gpt-4-turbo', 'claude-3-5-sonnet-20241022']
  },
  data: {
    primary: ['gpt-4o', 'claude-sonnet-4-20250514', 'gemini-2.5-pro'],
    fallback: ['gpt-4-turbo', 'deepseek-chat']
  },
  document: {
    primary: ['claude-sonnet-4-20250514', 'gpt-4o', 'gemini-2.5-pro'],
    fallback: ['claude-3-5-sonnet-20241022', 'gpt-4-turbo']
  },
  general: {
    primary: ['gpt-4o', 'claude-sonnet-4-20250514', 'gemini-2.0-flash'],
    fallback: ['gpt-4-turbo', 'deepseek-chat', 'gemini-2.5-flash']
  },
  // تولید تصویر
  'image-generation': {
    primary: ['dall-e-3', 'gemini-2.0-flash-preview-image-generation', 'imagen-3'],
    fallback: ['gemini-2.0-flash']
  },
  creative: {
    primary: ['dall-e-3', 'gemini-2.0-flash-preview-image-generation', 'gpt-4o', 'claude-sonnet-4-20250514'],
    fallback: ['imagen-3', 'gemini-2.0-flash']
  }
};

// ========================================
// 🔍 FILE DETECTION & SMART SELECTION
// ========================================

/**
 * تشخیص نوع فایل از روی extension و mimeType
 */
function detectFileCategory(fileName, mimeType) {
  const ext = (fileName || '').split('.').pop().toLowerCase();
  
  for (const [category, config] of Object.entries(FILE_CATEGORIES)) {
    // بررسی extension
    if (config.extensions && config.extensions.includes(ext)) {
      return { category, config, ext, mimeType };
    }
    
    // بررسی mimeType
    if (mimeType && config.mimeTypes) {
      for (const mimePrefix of config.mimeTypes) {
        if (mimeType.startsWith(mimePrefix) || mimeType.includes(mimePrefix)) {
          return { category, config, ext, mimeType };
        }
      }
    }
  }
  
  return { category: 'unknown', config: { icon: '❓', description: 'نامشخص', extractable: false }, ext, mimeType };
}

/**
 * تحلیل فایل‌های پیوست و تعیین قابلیت‌های مورد نیاز
 */
function analyzeAttachments(attachments) {
  if (!attachments || attachments.length === 0) {
    return {
      hasFiles: false,
      categories: [],
      requiredCapabilities: [],
      details: [],
      summary: 'بدون فایل پیوست'
    };
  }
  
  const categories = [];
  const requiredCapabilities = new Set();
  const details = [];
  
  for (const file of attachments) {
    const detection = detectFileCategory(file.name, file.mimeType);
    categories.push(detection);
    
    Logger.log(`📎 File: ${file.name} | MimeType: ${file.mimeType} | Category: ${detection.category}`);
    
    // تعیین قابلیت‌های مورد نیاز
    if (detection.config.requiresVision) requiredCapabilities.add('vision');
    if (detection.config.requiresCodeAnalysis) requiredCapabilities.add('code');
    if (detection.config.structured) requiredCapabilities.add('data');
    if (detection.config.requiresTranscription) requiredCapabilities.add('audio');
    
    // 🔥 تشخیص اضافی برای فایل‌های کد از روی محتوا یا نام
    const fileName = (file.name || '').toLowerCase();
    if (fileName.endsWith('.gs') || fileName.endsWith('.html') || fileName.endsWith('.js') || 
        fileName.endsWith('.py') || fileName.endsWith('.css') || fileName.endsWith('.jsx') ||
        fileName.includes('backend') || fileName.includes('frontend') || fileName.includes('code')) {
      requiredCapabilities.add('code');
      Logger.log(`  💻 Code file detected: ${file.name}`);
    }
    
    details.push({
      name: file.name,
      category: detection.category,
      icon: detection.config.icon,
      extractable: detection.config.extractable,
      requiresVision: detection.config.requiresVision
    });
  }
  
  // اگر هیچ قابلیت خاصی نیاز نبود، document یا general
  if (requiredCapabilities.size === 0) {
    const hasDocuments = categories.some(c => ['documents', 'word', 'pdf', 'markdown', 'ebook'].includes(c.category));
    if (hasDocuments) {
      requiredCapabilities.add('document');
    }
  }
  
  Logger.log(`🎯 Required capabilities: ${Array.from(requiredCapabilities).join(', ') || 'none'}`);
  
  return {
    hasFiles: true,
    count: attachments.length,
    categories: categories,
    requiredCapabilities: Array.from(requiredCapabilities),
    details: details,
    summary: `${attachments.length} فایل: ${details.map(d => d.icon).join(' ')}`,
    // 🆕 تخمین حجم توکن
    estimatedTokens: estimateTokens(attachments)
  };
}

/**
 * 🆕 تخمین تعداد توکن‌های فایل‌ها
 */
function estimateTokens(attachments) {
  if (!attachments || attachments.length === 0) return 0;
  
  let totalChars = 0;
  
  for (const file of attachments) {
    if (file.data) {
      // برای base64، هر 4 کاراکتر = 3 بایت
      const dataLength = file.data.length;
      
      // اگر تصویر است، فقط metadata
      if (file.mimeType && file.mimeType.startsWith('image/')) {
        totalChars += 1000; // تخمین برای توصیف تصویر
      } else {
        // برای متن، تبدیل از base64
        try {
          const decoded = Utilities.base64Decode(file.data);
          totalChars += decoded.length;
        } catch (e) {
          totalChars += dataLength * 0.75;
        }
      }
    }
  }
  
  // تخمین توکن: هر 4 کاراکتر ≈ 1 توکن
  return Math.ceil(totalChars / 4);
}

/**
 * انتخاب هوشمند مدل‌ها بر اساس تحلیل فایل‌ها و پرامپت
 * 🔥 نسخه بهبود یافته با بررسی context window و توکن
 */
// 🆕 Cache برای API های که خطا دادند (حافظه موقت)
const API_ERROR_CACHE = {};
const CACHE_DURATION_MS = 5 * 60 * 1000; // 5 دقیقه

/**
 * ثبت خطای API
 */
function recordApiError(provider, errorType) {
  API_ERROR_CACHE[provider] = {
    timestamp: Date.now(),
    errorType: errorType
  };
  Logger.log(`⚠️ API Error recorded for ${provider}: ${errorType}`);
}

/**
 * بررسی آیا API در وضعیت خطا است
 */
function isApiInErrorState(provider) {
  const error = API_ERROR_CACHE[provider];
  if (!error) return false;
  
  // اگر خطا قدیمی‌تر از 5 دقیقه است، پاک کن
  if (Date.now() - error.timestamp > CACHE_DURATION_MS) {
    delete API_ERROR_CACHE[provider];
    return false;
  }
  
  return true;
}

/**
 * پاک کردن cache خطاها
 */
function clearApiErrorCache() {
  Object.keys(API_ERROR_CACHE).forEach(key => delete API_ERROR_CACHE[key]);
  Logger.log('✅ API error cache cleared');
}

function smartSelectModelsAdvanced(prompt, attachments, mode) {
  try {
    const keys = getApiKeys();
    const analysis = analyzeAttachments(attachments);
    
    // اطمینان از اینکه requiredCapabilities آرایه است
    const requiredCaps = Array.isArray(analysis.requiredCapabilities) 
      ? analysis.requiredCapabilities 
      : [];
    
    // 🆕 تخمین توکن‌ها
    const estimatedTokens = analysis.estimatedTokens || estimateTokens(attachments);
    const promptTokens = Math.ceil((prompt || '').length / 4);
    const totalTokens = estimatedTokens + promptTokens;
    
    Logger.log('🎯 Smart Selection Analysis:');
    Logger.log('  - Files: ' + (analysis.summary || 'N/A'));
    Logger.log('  - Required: ' + (requiredCaps.length > 0 ? requiredCaps.join(', ') : 'none'));
    Logger.log('  - 📊 Estimated tokens: ' + totalTokens.toLocaleString());
    
    // تحلیل پرامپت
    const promptLower = (prompt || '').toLowerCase();
    const promptCapabilities = [];
    
    if (/کد|برنامه|code|function|debug|error|bug|script|develop|html|css|javascript|python|backend|frontend/i.test(prompt)) {
      promptCapabilities.push('code');
    }
    if (/تصویر|عکس|image|picture|photo|visual|screenshot/i.test(prompt)) {
      promptCapabilities.push('vision');
    }
    if (/داده|جدول|csv|excel|data|table|chart|graph/i.test(prompt)) {
      promptCapabilities.push('data');
    }
    if (/ترجم|translate|translation/i.test(prompt)) {
      promptCapabilities.push('document');
    }
    
    // 🎨 تشخیص درخواست تولید تصویر
    if (/نقاشی|بکش|رسم|طراحی|draw|paint|sketch|generate.*image|create.*image|make.*image|تولید.*تصویر|بساز.*عکس|ایجاد.*تصویر/i.test(prompt)) {
      promptCapabilities.push('image-generation');
      Logger.log('  🎨 Image generation detected!');
    }
    
    // ترکیب قابلیت‌های مورد نیاز
    const allCapabilities = [...new Set([...requiredCaps, ...promptCapabilities])];
    
    if (allCapabilities.length === 0) {
      allCapabilities.push('general');
    }
    
    Logger.log('  - All capabilities: ' + allCapabilities.join(', '));
    
    // پیدا کردن مدل‌های مناسب
    const suitableModels = [];
    const excludedModels = [];
    const usedProviders = new Set();
    
    // 🔥 اولویت‌بندی بر اساس context window
    const sortedModels = Object.entries(MODEL_REGISTRY)
      .map(([id, model]) => ({ id, ...model }))
      .filter(model => {
        // فیلتر اولیه
        if (!model.enabled) {
          excludedModels.push({ id: model.id || 'unknown', reason: 'غیرفعال' });
          return false;
        }
        if (!keys[model.provider]) {
          excludedModels.push({ id: model.id || 'unknown', reason: 'کلید API ندارد' });
          return false;
        }
        // 🆕 چک وضعیت خطای API
        if (isApiInErrorState(model.provider)) {
          excludedModels.push({ id: model.id || 'unknown', reason: 'API در وضعیت خطا' });
          Logger.log(`  ⏭️ Skipping ${model.provider}: API in error state`);
          return false;
        }
        return true;
      })
      .sort((a, b) => (b.contextWindow || 0) - (a.contextWindow || 0));
    
    for (const model of sortedModels) {
      const modelId = model.id;
      const contextWindow = model.contextWindow || 32000;
      
      // 🔥 مدل‌های تصویرساز فقط برای تولید تصویر
      if (model.isImageGenerator) {
        if (!allCapabilities.includes('image-generation')) {
          // اگر کار تولید تصویر نیست، Skip کن
          Logger.log(`  ⏭️ Skipping ${modelId}: Image generator not needed for this task`);
          continue;
        }
      }
      
      // بررسی قابلیت vision
      if (allCapabilities.includes('vision') && !model.supportsImages && !model.isImageGenerator) {
        continue;
      }
      
      // بررسی قابلیت تولید تصویر
      if (allCapabilities.includes('image-generation') && !model.isImageGenerator) {
        continue;
      }
      
      // تعیین دلیل انتخاب بر اساس قابلیت
      let reason = '';
      let modelPriority = model.priority || 5;
      
      if (model.isImageGenerator) {
        // فقط وقتی کار تولید تصویر است
        reason = '🎨 تولید تصویر';
        modelPriority = 1;
      } else if (allCapabilities.includes('code')) {
        // 🔥 اولویت بالا برای کدنویسی
        if (modelId.includes('coder')) {
          reason = '💻 تخصص کدنویسی';
          modelPriority = 0; // بالاترین اولویت
        } else if (modelId.includes('deepseek')) {
          reason = '💻 DeepSeek - کدنویسی';
          modelPriority = 1;
        } else if (modelId.includes('claude') || modelId.includes('gpt-4')) {
          reason = '🧠 هوش بالا برای کد';
          modelPriority = 2;
        } else if (contextWindow >= 100000) {
          reason = '📚 Context بزرگ برای کد (' + Math.round(contextWindow/1000) + 'K)';
          modelPriority = 3;
        } else {
          reason = '🔧 پردازش کد';
          modelPriority = 4;
        }
      } else if (contextWindow >= 100000) {
        reason = '📚 Context بزرگ (' + Math.round(contextWindow/1000) + 'K)';
        modelPriority = 2;
      } else {
        reason = 'مناسب برای ' + allCapabilities[0];
      }
      
      if (!suitableModels.find(m => m.id === modelId)) {
        suitableModels.push({
          id: modelId,
          name: model.name,
          provider: model.provider,
          priority: modelPriority,
          capabilities: allCapabilities,
          supportsImages: model.supportsImages,
          isImageGenerator: model.isImageGenerator || false,
          contextWindow: contextWindow,
          reason: reason
        });
        usedProviders.add(model.provider);
      }
    }
    
    // مرتب‌سازی بر اساس اولویت
    suitableModels.sort((a, b) => a.priority - b.priority);
    
    // انتخاب تعداد مناسب مدل بر اساس حالت
    const modeConfig = MODES[mode] || MODES.AUTO;
    let maxModels = 3;
    
    if (mode === 'QUICK') maxModels = 1;
    else if (mode === 'COLLABORATION') maxModels = 2;
    else if (mode === 'DEEP_RESEARCH') maxModels = 4;
    else if (allCapabilities.includes('image-generation')) maxModels = 2;
    
    const selected = suitableModels.slice(0, maxModels);
    
    Logger.log('✅ Selected models:');
    selected.forEach(m => Logger.log(`  - ${m.id}: ${m.reason} (context: ${m.contextWindow})`));
    
    if (excludedModels.length > 0) {
      Logger.log('⏭️ Excluded models:');
      excludedModels.slice(0, 5).forEach(m => Logger.log(`  - ${m.id}: ${m.reason}`));
    }
    
    // اگر مدلی پیدا نشد
    if (selected.length === 0) {
      let errorMsg = '';
      if (requiredCaps.includes('vision')) {
        errorMsg = 'برای پردازش تصویر، کلید API مدل‌های vision (OpenAI/Claude/Gemini) لازم است';
      } else {
        errorMsg = 'هیچ مدل فعالی با کلید API یافت نشد';
      }
      
      return {
        success: false,
        error: errorMsg,
        suggested: [],
        analysis: analysis,
        estimatedTokens: totalTokens,
        excludedModels: excludedModels
      };
    }
    
    Logger.log('✅ Final selection: ' + selected.map(m => m.id).join(', '));
    
    return {
      success: true,
      suggested: selected,
      all: suitableModels.slice(0, 10),
      analysis: analysis,
      requiredCapabilities: allCapabilities,
      estimatedTokens: totalTokens,
      excludedModels: excludedModels
    };
    
  } catch (error) {
    Logger.log('❌ Smart selection error: ' + error);
    return {
      success: false,
      error: error.toString(),
      suggested: []
    };
  }
}

// ========================================
// 📤 GENERATED FILES EXTRACTION
// ========================================

/**
 * استخراج فایل‌های تولیدی از پاسخ مدل
 */
function extractGeneratedFiles(response, modelId, promptId) {
  const files = [];
  
  if (!response || typeof response !== 'string') return files;
  
  // استخراج بلوک‌های کد
  const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
  let match;
  let codeIndex = 1;
  
  while ((match = codeBlockRegex.exec(response)) !== null) {
    const language = match[1] || 'txt';
    const code = match[2].trim();
    
    if (code.length > 50) { // فقط کدهای با معنی
      const ext = getExtensionForLanguage(language);
      const fileName = `generated_${promptId}_${codeIndex}.${ext}`;
      
      files.push({
        type: 'code',
        language: language,
        extension: ext,
        fileName: fileName,
        content: code,
        size: code.length,
        model: modelId,
        icon: '💻'
      });
      
      codeIndex++;
    }
  }
  
  // استخراج JSON
  const jsonRegex = /\{[\s\S]*?\}/g;
  let jsonIndex = 1;
  while ((match = jsonRegex.exec(response)) !== null) {
    try {
      const json = JSON.parse(match[0]);
      if (Object.keys(json).length > 2) { // فقط JSON های با معنی
        const content = JSON.stringify(json, null, 2);
        files.push({
          type: 'data',
          language: 'json',
          extension: 'json',
          fileName: `data_${promptId}_${jsonIndex}.json`,
          content: content,
          size: content.length,
          model: modelId,
          icon: '📋'
        });
        jsonIndex++;
      }
    } catch (e) {
      // نه JSON معتبر
    }
  }
  
  // استخراج جداول Markdown
  const tableRegex = /\|[\s\S]*?\|[\s\S]*?\n(?:\|[-:]+)+\|[\s\S]*?(?=\n\n|$)/g;
  let tableIndex = 1;
  while ((match = tableRegex.exec(response)) !== null) {
    const table = match[0].trim();
    if (table.split('\n').length > 2) {
      // تبدیل به CSV
      const csvContent = markdownTableToCsv(table);
      files.push({
        type: 'data',
        language: 'csv',
        extension: 'csv',
        fileName: `table_${promptId}_${tableIndex}.csv`,
        content: csvContent,
        size: csvContent.length,
        model: modelId,
        icon: '📊'
      });
      tableIndex++;
    }
  }
  
  Logger.log(`📦 Extracted ${files.length} files from ${modelId}`);
  return files;
}

/**
 * دریافت پسوند فایل برای زبان برنامه‌نویسی
 */
function getExtensionForLanguage(language) {
  const langMap = {
    'javascript': 'js', 'js': 'js',
    'typescript': 'ts', 'ts': 'ts',
    'python': 'py', 'py': 'py',
    'java': 'java',
    'cpp': 'cpp', 'c++': 'cpp', 'c': 'c',
    'csharp': 'cs', 'cs': 'cs',
    'go': 'go', 'golang': 'go',
    'rust': 'rs',
    'ruby': 'rb',
    'php': 'php',
    'swift': 'swift',
    'kotlin': 'kt',
    'html': 'html',
    'css': 'css',
    'scss': 'scss',
    'sql': 'sql',
    'bash': 'sh', 'shell': 'sh', 'sh': 'sh',
    'powershell': 'ps1',
    'json': 'json',
    'yaml': 'yaml', 'yml': 'yaml',
    'xml': 'xml',
    'markdown': 'md', 'md': 'md',
    'text': 'txt', 'txt': 'txt',
    'plaintext': 'txt'
  };
  
  return langMap[language.toLowerCase()] || 'txt';
}

/**
 * تبدیل جدول Markdown به CSV
 */
function markdownTableToCsv(markdownTable) {
  const lines = markdownTable.trim().split('\n');
  const csvLines = [];
  
  for (const line of lines) {
    // حذف خطوط جداکننده
    if (line.match(/^\|[-:|\s]+\|$/)) continue;
    
    // استخراج سلول‌ها
    const cells = line.split('|')
      .map(cell => cell.trim())
      .filter(cell => cell.length > 0);
    
    // Escape کردن برای CSV
    const csvCells = cells.map(cell => {
      if (cell.includes(',') || cell.includes('"') || cell.includes('\n')) {
        return '"' + cell.replace(/"/g, '""') + '"';
      }
      return cell;
    });
    
    csvLines.push(csvCells.join(','));
  }
  
  return csvLines.join('\n');
}

/**
 * ذخیره فایل تولیدی در Google Drive
 */
function saveGeneratedFile(fileData, promptId) {
  try {
    const folder = DriveApp.getFolderById(CONFIG.generatedFilesFolderId || CONFIG.folderId);
    
    // ایجاد زیرپوشه برای این پرامپت
    let promptFolder;
    const existingFolders = folder.getFoldersByName('Generated_' + promptId);
    if (existingFolders.hasNext()) {
      promptFolder = existingFolders.next();
    } else {
      promptFolder = folder.createFolder('Generated_' + promptId);
    }
    
    // ذخیره فایل
    const blob = Utilities.newBlob(fileData.content, 'text/plain', fileData.fileName);
    const file = promptFolder.createFile(blob);
    
    Logger.log(`✅ Saved: ${fileData.fileName} → ${file.getUrl()}`);
    
    return {
      success: true,
      fileId: file.getId(),
      fileName: fileData.fileName,
      url: file.getUrl(),
      downloadUrl: file.getDownloadUrl(),
      size: fileData.size
    };
    
  } catch (error) {
    Logger.log(`❌ Error saving file: ${error}`);
    return {
      success: false,
      error: error.toString()
    };
  }
}

/**
 * ذخیره همه فایل‌های تولیدی یک پرامپت
 */
function saveAllGeneratedFiles(responses, promptId) {
  const savedFiles = [];
  
  for (const resp of responses) {
    if (!resp.response) continue;
    
    const extractedFiles = extractGeneratedFiles(resp.response, resp.model, promptId);
    
    for (const file of extractedFiles) {
      const saved = saveGeneratedFile(file, promptId);
      if (saved.success) {
        savedFiles.push({
          ...file,
          url: saved.url,
          downloadUrl: saved.downloadUrl,
          fileId: saved.fileId
        });
      }
    }
  }
  
  return savedFiles;
}

// ========================================
// 📥 EXPORT & DOWNLOAD FUNCTIONS
// ========================================

/**
 * ایجاد خروجی کامل از نتایج مناظره
 */
function generateFullExport(promptId) {
  try {
    const archiveResult = loadArchiveDetails(promptId);
    if (!archiveResult) {
      return { success: false, error: 'پرونده یافت نشد' };
    }
    
    const timestamp = new Date().toISOString().slice(0, 10);
    const exportData = {
      metadata: {
        promptId: promptId,
        exportDate: new Date().toISOString(),
        version: '10.0'
      },
      prompt: archiveResult.prompt,
      mode: archiveResult.mode,
      models: archiveResult.models,
      rounds: archiveResult.rounds || [],
      scores: archiveResult.scores || [],
      judge: archiveResult.judge || null,
      summary: archiveResult.summary || '',
      generatedFiles: archiveResult.generatedFiles || []
    };
    
    // ایجاد فایل‌های مختلف
    const exports = [];
    
    // 1. JSON کامل
    const jsonContent = JSON.stringify(exportData, null, 2);
    const jsonBlob = Utilities.newBlob(jsonContent, 'application/json', `debate_${promptId}_${timestamp}.json`);
    
    // 2. Markdown خوانا
    const mdContent = generateMarkdownExport(exportData);
    const mdBlob = Utilities.newBlob(mdContent, 'text/markdown', `debate_${promptId}_${timestamp}.md`);
    
    // 3. HTML زیبا
    const htmlContent = generateHtmlExport(exportData);
    const htmlBlob = Utilities.newBlob(htmlContent, 'text/html', `debate_${promptId}_${timestamp}.html`);
    
    // ذخیره در Drive
    const folder = DriveApp.getFolderById(CONFIG.outputFolderId || CONFIG.folderId);
    
    const jsonFile = folder.createFile(jsonBlob);
    const mdFile = folder.createFile(mdBlob);
    const htmlFile = folder.createFile(htmlBlob);
    
    exports.push({
      type: 'json',
      name: jsonBlob.getName(),
      url: jsonFile.getUrl(),
      downloadUrl: jsonFile.getDownloadUrl(),
      icon: '📋'
    });
    
    exports.push({
      type: 'markdown',
      name: mdBlob.getName(),
      url: mdFile.getUrl(),
      downloadUrl: mdFile.getDownloadUrl(),
      icon: '📝'
    });
    
    exports.push({
      type: 'html',
      name: htmlBlob.getName(),
      url: htmlFile.getUrl(),
      downloadUrl: htmlFile.getDownloadUrl(),
      icon: '🌐'
    });
    
    return {
      success: true,
      exports: exports,
      promptId: promptId,
      timestamp: timestamp
    };
    
  } catch (error) {
    Logger.log('❌ Export error: ' + error);
    return {
      success: false,
      error: error.toString()
    };
  }
}

/**
 * تولید خروجی Markdown
 */
function generateMarkdownExport(data) {
  let md = `# 🤖 نتایج مناظره هوش مصنوعی\n\n`;
  md += `📅 **تاریخ:** ${new Date().toLocaleDateString('fa-IR')}\n`;
  md += `🆔 **شناسه:** ${data.metadata.promptId}\n`;
  md += `🎯 **حالت:** ${data.mode}\n\n`;
  
  md += `## 📝 پرامپت\n\n${data.prompt}\n\n`;
  
  md += `## 🤖 مدل‌های شرکت‌کننده\n\n`;
  if (data.models && Array.isArray(data.models)) {
    data.models.forEach(m => {
      md += `- ${m}\n`;
    });
  }
  md += '\n';
  
  md += `## 🎯 دورهای مناظره\n\n`;
  if (data.rounds && data.rounds.length > 0) {
    data.rounds.forEach(round => {
      md += `### دور ${round.round} - ${round.model}\n\n`;
      md += `${round.response || 'بدون پاسخ'}\n\n`;
      md += `---\n\n`;
    });
  }
  
  if (data.scores && data.scores.length > 0) {
    md += `## ⭐ امتیازات\n\n`;
    md += `| امتیازدهنده | هدف | امتیاز |\n`;
    md += `|------------|-----|-------|\n`;
    data.scores.forEach(s => {
      md += `| ${s.scorer} | ${s.target} | ${s.total}/100 |\n`;
    });
    md += '\n';
  }
  
  if (data.judge) {
    md += `## ⚖️ داوری\n\n`;
    md += `**داور:** ${data.judge.judge}\n`;
    md += `**برنده:** ${data.judge.winner}\n`;
    md += `**دلیل:** ${data.judge.reasoning}\n\n`;
  }
  
  if (data.summary) {
    md += `## 📋 خلاصه\n\n${data.summary}\n\n`;
  }
  
  if (data.generatedFiles && data.generatedFiles.length > 0) {
    md += `## 📦 فایل‌های تولیدی\n\n`;
    data.generatedFiles.forEach(f => {
      md += `- ${f.icon} [${f.fileName}](${f.url})\n`;
    });
  }
  
  md += `\n---\n*تولید شده توسط سیستم مناظره هوش مصنوعی v10.0*\n`;
  
  return md;
}

/**
 * تولید خروجی HTML زیبا
 */
function generateHtmlExport(data) {
  return `<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>نتایج مناظره - ${data.metadata.promptId}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { 
      font-family: Tahoma, Arial, sans-serif; 
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      min-height: 100vh;
      padding: 20px;
    }
    .container { 
      max-width: 900px; 
      margin: 0 auto; 
      background: white;
      border-radius: 20px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.3);
      overflow: hidden;
    }
    .header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 30px;
      text-align: center;
    }
    .header h1 { font-size: 24px; margin-bottom: 10px; }
    .header .meta { font-size: 14px; opacity: 0.9; }
    .content { padding: 30px; }
    .section { 
      margin-bottom: 30px; 
      background: #f8f9fa;
      border-radius: 12px;
      padding: 20px;
    }
    .section h2 { 
      color: #667eea; 
      font-size: 18px; 
      margin-bottom: 15px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .prompt-box {
      background: white;
      border-right: 4px solid #667eea;
      padding: 15px;
      border-radius: 8px;
      line-height: 1.8;
    }
    .round {
      background: white;
      border-radius: 10px;
      padding: 15px;
      margin-bottom: 15px;
    }
    .round-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 10px;
      padding-bottom: 10px;
      border-bottom: 1px solid #eee;
    }
    .model-name { font-weight: bold; color: #667eea; }
    .round-content { line-height: 1.8; color: #333; }
    .scores-table {
      width: 100%;
      border-collapse: collapse;
    }
    .scores-table th, .scores-table td {
      padding: 12px;
      text-align: center;
      border-bottom: 1px solid #eee;
    }
    .scores-table th { background: #667eea; color: white; }
    .scores-table tr:hover { background: #f0f0f0; }
    .winner-box {
      background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
      color: white;
      padding: 20px;
      border-radius: 12px;
      text-align: center;
    }
    .winner-box h3 { font-size: 24px; margin-bottom: 10px; }
    .files-list { list-style: none; }
    .files-list li {
      background: white;
      padding: 12px;
      margin-bottom: 8px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .files-list a { color: #667eea; text-decoration: none; }
    .files-list a:hover { text-decoration: underline; }
    .footer {
      text-align: center;
      padding: 20px;
      color: #888;
      font-size: 12px;
      border-top: 1px solid #eee;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🤖 نتایج مناظره هوش مصنوعی</h1>
      <div class="meta">
        📅 ${new Date().toLocaleDateString('fa-IR')} | 
        🆔 ${data.metadata.promptId} | 
        🎯 ${data.mode}
      </div>
    </div>
    
    <div class="content">
      <div class="section">
        <h2>📝 پرامپت</h2>
        <div class="prompt-box">${data.prompt}</div>
      </div>
      
      <div class="section">
        <h2>🎯 دورهای مناظره</h2>
        ${(data.rounds || []).map(r => `
          <div class="round">
            <div class="round-header">
              <span class="model-name">${r.model}</span>
              <span>دور ${r.round}</span>
            </div>
            <div class="round-content">${(r.response || '').replace(/\n/g, '<br>')}</div>
          </div>
        `).join('')}
      </div>
      
      ${data.scores && data.scores.length > 0 ? `
        <div class="section">
          <h2>⭐ امتیازات</h2>
          <table class="scores-table">
            <tr><th>امتیازدهنده</th><th>هدف</th><th>امتیاز</th></tr>
            ${data.scores.map(s => `
              <tr>
                <td>${s.scorer}</td>
                <td>${s.target}</td>
                <td><strong>${s.total}/100</strong></td>
              </tr>
            `).join('')}
          </table>
        </div>
      ` : ''}
      
      ${data.judge ? `
        <div class="section">
          <h2>⚖️ داوری</h2>
          <div class="winner-box">
            <h3>🏆 ${data.judge.winner}</h3>
            <p>${data.judge.reasoning}</p>
          </div>
        </div>
      ` : ''}
      
      ${data.summary ? `
        <div class="section">
          <h2>📋 خلاصه</h2>
          <div class="prompt-box">${data.summary.replace(/\n/g, '<br>')}</div>
        </div>
      ` : ''}
      
      ${data.generatedFiles && data.generatedFiles.length > 0 ? `
        <div class="section">
          <h2>📦 فایل‌های تولیدی</h2>
          <ul class="files-list">
            ${data.generatedFiles.map(f => `
              <li>
                <span>${f.icon}</span>
                <a href="${f.url}" target="_blank">${f.fileName}</a>
              </li>
            `).join('')}
          </ul>
        </div>
      ` : ''}
    </div>
    
    <div class="footer">
      تولید شده توسط سیستم مناظره هوش مصنوعی v10.0
    </div>
  </div>
</body>
</html>`;
}

/**
 * دریافت لیست فرمت‌های پشتیبانی شده
 */
function getSupportedFileTypes() {
  const types = [];
  
  for (const [category, config] of Object.entries(FILE_CATEGORIES)) {
    types.push({
      category: category,
      icon: config.icon,
      description: config.description,
      extensions: config.extensions,
      extractable: config.extractable,
      requiresVision: config.requiresVision
    });
  }
  
  return {
    success: true,
    categories: types,
    totalExtensions: types.reduce((sum, t) => sum + (t.extensions?.length || 0), 0)
  };
}

/**
 * دریافت API Keys از Script Properties (امن)
 */
function getApiKeys() {
  try {
    const props = PropertiesService.getScriptProperties();
    return {
      openai: props.getProperty('OPENAI_API_KEY'),
      claude: props.getProperty('CLAUDE_API_KEY'),
      deepseek: props.getProperty('DEEPSEEK_API_KEY'),
      gemini: props.getProperty('GEMINI_API_KEY'),
      openrouter: props.getProperty('OPENROUTER_API_KEY'),
      groq: props.getProperty('GROQ_API_KEY')
    };
  } catch (error) {
    Logger.log('❌ Error getting API keys: ' + error);
    return { openai: null, claude: null, deepseek: null, gemini: null, openrouter: null, groq: null };
  }
}

function getApiKey(provider) {
  const keys = getApiKeys();
  return keys[provider] || null;
}

// حالت‌های کاری
const MODES = {
  AUTO: { name: 'تشخیص خودکار', icon: '🤖', rounds: 2, scoring: true, judge: true, summary: true, roles: ['ANALYZER', 'CRITIC', 'CODER'] },
  DEBATE: { name: 'مناظره', icon: '🥊', rounds: 2, scoring: true, judge: true, summary: true, roles: ['DEBATER_PRO', 'DEBATER_CON'] },
  COLLABORATION: { name: 'همکاری', icon: '🤝', rounds: 1, scoring: true, judge: true, summary: true, roles: ['ANALYZER', 'CODER', 'REVIEWER'] },
  DEEP_RESEARCH: { name: 'تحقیق عمیق', icon: '🔍', rounds: 3, scoring: true, judge: true, summary: true, roles: ['RESEARCHER', 'ANALYST', 'SYNTHESIZER'] },
  QUICK: { name: 'سریع', icon: '⚡', rounds: 1, scoring: false, judge: false, summary: false, roles: ['RESPONDER'] },
  CREATIVE: { name: 'خلاقانه', icon: '🎨', rounds: 2, scoring: true, judge: true, summary: true, roles: ['IDEATOR', 'CRITIC', 'REFINER'] }
};

// ========================================
// 🎭 AI ROLES - نقش‌های هوش مصنوعی
// ========================================

const AI_ROLES = {
  // نقش‌های عمومی
  ANALYZER: {
    name: 'تحلیلگر',
    icon: '🔬',
    description: 'تحلیل عمیق و دقیق محتوا',
    systemPrompt: `شما یک تحلیلگر متخصص هستید. وظیفه شما:
- تحلیل دقیق و عمیق محتوا
- شناسایی نقاط کلیدی و مهم
- ارائه تحلیل ساختارمند و جامع
- توجه به جزئیات فنی`,
    bestModels: ['claude-sonnet-4-20250514', 'gpt-4-turbo', 'gpt-4o'],
    capabilities: ['reasoning', 'text']
  },
  
  CRITIC: {
    name: 'منتقد',
    icon: '🔍',
    description: 'بررسی خطاها و نقاط ضعف',
    systemPrompt: `شما یک منتقد حرفه‌ای هستید. وظیفه شما:
- یافتن خطاها و مشکلات
- شناسایی نقاط ضعف
- ارائه نقد سازنده
- پیشنهاد اصلاحات مشخص
به هیچ وجه تعارف نکنید! صادق باشید.`,
    bestModels: ['gpt-4-turbo', 'claude-3-5-sonnet-20241022', 'deepseek-chat'],
    capabilities: ['reasoning']
  },
  
  CODER: {
    name: 'کدنویس',
    icon: '👨‍💻',
    description: 'نوشتن و بررسی کد',
    systemPrompt: `شما یک برنامه‌نویس ارشد هستید. وظیفه شما:
- نوشتن کد تمیز و بهینه
- رعایت best practices
- مستندسازی کامل
- رسیدگی به edge cases
کد کامل و قابل اجرا بدهید!`,
    bestModels: ['deepseek-coder', 'claude-sonnet-4-20250514', 'gpt-4-turbo'],
    capabilities: ['code']
  },
  
  IDEATOR: {
    name: 'ایده‌پرداز',
    icon: '💡',
    description: 'ایده‌پردازی و خلاقیت',
    systemPrompt: `شما یک ایده‌پرداز خلاق هستید. وظیفه شما:
- ارائه ایده‌های نوآورانه
- پیشنهاد راه‌حل‌های جایگزین
- تفکر خارج از چارچوب
- ترکیب مفاهیم به شکل جدید`,
    bestModels: ['gpt-4o', 'claude-sonnet-4-20250514', 'gemini-2.0-flash'],
    capabilities: ['text']
  },
  
  REVIEWER: {
    name: 'بازبین',
    icon: '👁️',
    description: 'بررسی و کنترل کیفیت',
    systemPrompt: `شما یک بازبین کیفیت هستید. وظیفه شما:
- بررسی انسجام و یکپارچگی
- اطمینان از پوشش کامل موضوع
- کنترل کیفیت نهایی
- جمع‌بندی و نتیجه‌گیری`,
    bestModels: ['claude-sonnet-4-20250514', 'gpt-4-turbo'],
    capabilities: ['reasoning']
  },
  
  RESEARCHER: {
    name: 'محقق',
    icon: '📚',
    description: 'تحقیق و جمع‌آوری اطلاعات',
    systemPrompt: `شما یک محقق هستید. وظیفه شما:
- جمع‌آوری اطلاعات جامع
- ارائه منابع و مراجع
- تحلیل داده‌ها
- ارائه گزارش ساختارمند`,
    bestModels: ['gemini-2.0-flash', 'claude-sonnet-4-20250514', 'gpt-4-turbo'],
    capabilities: ['text', 'long-context']
  },
  
  // نقش‌های مناظره
  DEBATER_PRO: {
    name: 'موافق',
    icon: '👍',
    description: 'دفاع از موضع موافق',
    systemPrompt: `شما در نقش موافق هستید. وظیفه شما:
- دفاع قوی از موضع موافق
- ارائه دلایل و مستندات
- پاسخ به انتقادات طرف مقابل
- استدلال منطقی و محکم`,
    bestModels: ['claude-sonnet-4-20250514', 'gpt-4-turbo'],
    capabilities: ['reasoning']
  },
  
  DEBATER_CON: {
    name: 'مخالف',
    icon: '👎',
    description: 'دفاع از موضع مخالف',
    systemPrompt: `شما در نقش مخالف هستید. وظیفه شما:
- نقد و چالش موضع موافق
- ارائه دلایل مخالفت
- شناسایی نقاط ضعف استدلال‌ها
- پیشنهاد دیدگاه‌های جایگزین`,
    bestModels: ['gpt-4-turbo', 'claude-3-5-sonnet-20241022'],
    capabilities: ['reasoning']
  },
  
  // نقش‌های خاص
  SYNTHESIZER: {
    name: 'ترکیب‌کننده',
    icon: '🔄',
    description: 'ترکیب و جمع‌بندی نظرات',
    systemPrompt: `شما ترکیب‌کننده هستید. وظیفه شما:
- جمع‌آوری نقاط مشترک
- ترکیب دیدگاه‌های مختلف
- ایجاد راه‌حل جامع
- ارائه نتیجه‌گیری نهایی`,
    bestModels: ['claude-sonnet-4-20250514', 'gpt-4o'],
    capabilities: ['reasoning', 'text']
  },
  
  REFINER: {
    name: 'اصلاح‌کننده',
    icon: '✨',
    description: 'بهبود و اصلاح نتایج',
    systemPrompt: `شما اصلاح‌کننده هستید. وظیفه شما:
- بهبود کیفیت خروجی
- اصلاح خطاها
- پولیش نهایی
- اطمینان از کمال کار`,
    bestModels: ['claude-sonnet-4-20250514', 'gpt-4-turbo'],
    capabilities: ['text']
  },
  
  RESPONDER: {
    name: 'پاسخ‌دهنده',
    icon: '💬',
    description: 'پاسخ سریع و مستقیم',
    systemPrompt: `شما پاسخ‌دهنده سریع هستید. وظیفه شما:
- پاسخ مستقیم و کوتاه
- بدون حاشیه‌روی
- دقیق و کاربردی`,
    bestModels: ['gpt-4o-mini', 'claude-3-haiku-20240307', 'gemini-2.0-flash'],
    capabilities: ['fast-response']
  },
  
  ANALYST: {
    name: 'تحلیل‌گر داده',
    icon: '📊',
    description: 'تحلیل داده‌ها و آمار',
    systemPrompt: `شما تحلیل‌گر داده هستید. وظیفه شما:
- تحلیل آماری
- شناسایی الگوها
- ارائه بینش‌های کاربردی
- تصویرسازی داده‌ها`,
    bestModels: ['gpt-4-turbo', 'claude-sonnet-4-20250514'],
    capabilities: ['reasoning', 'code']
  }
};

// نقش‌های پیش‌فرض برای هر حالت
const MODE_ROLES = {
  AUTO: ['ANALYZER', 'CRITIC', 'CODER'],
  DEBATE: ['DEBATER_PRO', 'DEBATER_CON'],
  COLLABORATION: ['ANALYZER', 'CODER', 'REVIEWER'],
  DEEP_RESEARCH: ['RESEARCHER', 'ANALYST', 'SYNTHESIZER'],
  CREATIVE: ['IDEATOR', 'CRITIC', 'REFINER'],
  QUICK: ['RESPONDER']
};

// ========================================
// 📋 WORK SHEET SYSTEM - سیستم بساط کار
// ========================================

// وضعیت‌های مراحل
const STEP_STATUS = {
  PENDING: '⏳ در انتظار',
  RUNNING: '🔄 در حال اجرا',
  DONE: '✅ تکمیل شده',
  ERROR: '❌ خطا',
  SKIPPED: '⏭️ رد شده',
  PAUSED: '⏸️ متوقف'
};

// مراحل پردازش
const PROCESS_STEPS = {
  INIT: { order: 1, name: 'آماده‌سازی', icon: '🚀' },
  ANALYZE_CONTENT: { order: 2, name: 'تحلیل محتوا', icon: '📋' },
  SELECT_MODELS: { order: 3, name: 'انتخاب مدل‌ها', icon: '🤖' },
  ASSIGN_ROLES: { order: 4, name: 'تخصیص نقش‌ها', icon: '🎭' },
  PREPARE_FILES: { order: 5, name: 'آماده‌سازی فایل‌ها', icon: '📁' },
  ROUND_1: { order: 6, name: 'دور اول', icon: '1️⃣' },
  ROUND_2: { order: 7, name: 'دور دوم', icon: '2️⃣' },
  ROUND_3: { order: 8, name: 'دور سوم', icon: '3️⃣' },
  SCORING: { order: 9, name: 'امتیازدهی', icon: '📊' },
  JUDGING: { order: 10, name: 'داوری', icon: '⚖️' },
  SUMMARY: { order: 11, name: 'خلاصه‌نویسی', icon: '📝' },
  FINALIZE: { order: 12, name: 'نهایی‌سازی', icon: '🏁' }
};

/**
 * ایجاد Work Sheet برای یک پردازش جدید
 */
function createWorkSheet(promptId, prompt, mode, attachments) {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    const sheetName = '🔧 Work_' + promptId.substring(3, 18);
    
    // حذف Sheet قبلی اگر وجود دارد
    let existingSheet = ss.getSheetByName(sheetName);
    if (existingSheet) {
      ss.deleteSheet(existingSheet);
    }
    
    // ایجاد Sheet جدید
    const sheet = ss.insertSheet(sheetName);
    
    // ===== بخش 1: اطلاعات کلی (ردیف 1-5) =====
    sheet.getRange('A1:B1').setValues([['🔑 شناسه پردازش', promptId]]);
    sheet.getRange('C1:D1').setValues([['🎯 حالت', MODES[mode].name + ' ' + MODES[mode].icon]]);
    sheet.getRange('E1:F1').setValues([['📅 شروع', new Date().toLocaleString('fa-IR')]]);
    sheet.getRange('G1:H1').setValues([['📊 وضعیت', STEP_STATUS.RUNNING]]);
    
    sheet.getRange('A2:H2').setValues([[
      '📝 پرامپت:', prompt.substring(0, 200) + (prompt.length > 200 ? '...' : ''), '', '', '', '', '', ''
    ]]);
    sheet.getRange('A2:H2').merge();
    
    sheet.getRange('A3:B3').setValues([['📎 تعداد فایل', attachments ? attachments.length : 0]]);
    sheet.getRange('C3:D3').setValues([['🔄 دورها', MODES[mode].rounds]]);
    sheet.getRange('E3:F3').setValues([['⚖️ داوری', MODES[mode].judge ? 'بله' : 'خیر']]);
    sheet.getRange('G3:H3').setValues([['📋 خلاصه', MODES[mode].summary ? 'بله' : 'خیر']]);
    
    // استایل هدر
    sheet.getRange('A1:H3').setBackground('#e3f2fd').setFontWeight('bold');
    
    // ===== بخش 2: مدل‌ها و نقش‌ها (ردیف 5-12) =====
    sheet.getRange('A5:H5').setValues([['🤖 مدل‌ها و نقش‌ها', '', '', '', '', '', '', '']]);
    sheet.getRange('A5:H5').merge().setBackground('#fff3e0').setFontWeight('bold');
    
    sheet.getRange('A6:H6').setValues([['#', 'مدل', 'نقش', 'آیکون', 'وضعیت', 'توکن', 'زمان', 'یادداشت']]);
    sheet.getRange('A6:H6').setBackground('#ffe0b2').setFontWeight('bold');
    
    // ردیف‌های خالی برای مدل‌ها
    for (let i = 7; i <= 14; i++) {
      sheet.getRange(`A${i}:H${i}`).setValues([[i-6, '', '', '', STEP_STATUS.PENDING, 0, '', '']]);
    }
    
    // ===== بخش 3: مراحل پردازش (ردیف 16+) =====
    sheet.getRange('A16:H16').setValues([['📋 مراحل پردازش', '', '', '', '', '', '', '']]);
    sheet.getRange('A16:H16').merge().setBackground('#e8f5e9').setFontWeight('bold');
    
    sheet.getRange('A17:H17').setValues([['#', 'مرحله', 'آیکون', 'وضعیت', 'شروع', 'پایان', 'نتیجه', 'خطا']]);
    sheet.getRange('A17:H17').setBackground('#c8e6c9').setFontWeight('bold');
    
    // اضافه کردن مراحل
    let row = 18;
    Object.entries(PROCESS_STEPS).forEach(([key, step]) => {
      sheet.getRange(`A${row}:H${row}`).setValues([
        [step.order, step.name, step.icon, STEP_STATUS.PENDING, '', '', '', '']
      ]);
      row++;
    });
    
    // ===== بخش 4: پاسخ‌ها (ردیف 32+) =====
    sheet.getRange('A32:H32').setValues([['💬 پاسخ‌های مدل‌ها', '', '', '', '', '', '', '']]);
    sheet.getRange('A32:H32').merge().setBackground('#f3e5f5').setFontWeight('bold');
    
    sheet.getRange('A33:H33').setValues([['دور', 'مدل', 'نقش', 'پاسخ (خلاصه)', 'طول کامل', 'توکن', 'زمان', 'وضعیت']]);
    sheet.getRange('A33:H33').setBackground('#e1bee7').setFontWeight('bold');
    
    // ===== بخش 5: نتایج نهایی (ردیف 55+) =====
    sheet.getRange('A55:H55').setValues([['🏆 نتایج نهایی', '', '', '', '', '', '', '']]);
    sheet.getRange('A55:H55').merge().setBackground('#ffebee').setFontWeight('bold');
    
    // تنظیم عرض ستون‌ها
    sheet.setColumnWidth(1, 50);   // A
    sheet.setColumnWidth(2, 180);  // B
    sheet.setColumnWidth(3, 100);  // C
    sheet.setColumnWidth(4, 300);  // D - پاسخ/نتیجه
    sheet.setColumnWidth(5, 100);  // E
    sheet.setColumnWidth(6, 100);  // F
    sheet.setColumnWidth(7, 100);  // G
    sheet.setColumnWidth(8, 200);  // H
    
    // Freeze
    sheet.setFrozenRows(1);
    
    // رنگ تب
    sheet.setTabColor('#ff9800');
    
    Logger.log('📋 Work Sheet ایجاد شد: ' + sheetName);
    
    return sheet;
    
  } catch (error) {
    Logger.log('❌ خطا در ایجاد Work Sheet: ' + error);
    throw error;
  }
}

/**
 * آپدیت وضعیت یک مرحله در Work Sheet
 */
function updateWorkSheetStep(sheet, stepKey, status, result, error) {
  try {
    if (!sheet) return;
    
    const step = PROCESS_STEPS[stepKey];
    if (!step) return;
    
    const row = 17 + step.order; // ردیف 18 به بعد
    
    // آپدیت وضعیت
    sheet.getRange(`D${row}`).setValue(status);
    
    // زمان
    if (status === STEP_STATUS.RUNNING) {
      sheet.getRange(`E${row}`).setValue(new Date().toLocaleTimeString('fa-IR'));
    } else if (status === STEP_STATUS.DONE || status === STEP_STATUS.ERROR) {
      sheet.getRange(`F${row}`).setValue(new Date().toLocaleTimeString('fa-IR'));
    }
    
    // نتیجه
    if (result) {
      const resultStr = typeof result === 'object' ? JSON.stringify(result).substring(0, 200) : result.toString().substring(0, 200);
      sheet.getRange(`G${row}`).setValue(resultStr);
    }
    
    // خطا
    if (error) {
      sheet.getRange(`H${row}`).setValue(error.substring(0, 200));
      sheet.getRange(`A${row}:H${row}`).setBackground('#ffcdd2');
    } else if (status === STEP_STATUS.DONE) {
      sheet.getRange(`A${row}:H${row}`).setBackground('#c8e6c9');
    } else if (status === STEP_STATUS.RUNNING) {
      sheet.getRange(`A${row}:H${row}`).setBackground('#fff9c4');
    }
    
    SpreadsheetApp.flush();
    
  } catch (e) {
    Logger.log('⚠️ خطا در آپدیت وضعیت: ' + e);
  }
}

/**
 * ذخیره اطلاعات مدل‌ها و نقش‌ها در Work Sheet
 */
function saveModelsToWorkSheet(sheet, roleAssignments) {
  try {
    if (!sheet || !roleAssignments) return;
    
    let row = 7;
    roleAssignments.forEach((assignment, idx) => {
      if (row <= 14) {
        sheet.getRange(`A${row}:H${row}`).setValues([[
          idx + 1,
          assignment.modelId || '',
          assignment.roleName || '',
          assignment.icon || '',
          STEP_STATUS.PENDING,
          0,
          '',
          assignment.isJudge ? 'داور' : (assignment.isSummarizer ? 'خلاصه‌نویس' : '')
        ]]);
        row++;
      }
    });
    
    SpreadsheetApp.flush();
    
  } catch (e) {
    Logger.log('⚠️ خطا در ذخیره مدل‌ها: ' + e);
  }
}

/**
 * ذخیره وضعیت پردازش برای ادامه
 */
function saveWorkSheetState(sheet, state) {
  try {
    if (!sheet) return;
    
    // 🔥 ساخت state فشرده - بدون پاسخ‌های کامل
    const compactState = {
      promptId: state.promptId,
      prompt: state.prompt ? state.prompt.substring(0, 500) : '',  // فقط 500 کاراکتر اول
      mode: state.mode,
      status: state.status,
      models: state.models,
      totalRounds: state.totalRounds,
      currentRound: state.currentRound,
      
      // فقط metadata از دورها - نه پاسخ‌های کامل
      completedRoundsCount: state.completedRounds?.length || 0,
      
      // پاسخ‌های partial فعلی - فقط کلیدها
      currentRoundModelsCompleted: state.currentRoundResponses ? Object.keys(state.currentRoundResponses) : [],
      
      // وضعیت مراحل
      scoringDone: state.scoringDone || false,
      judgeDone: state.judgeDone || false,
      summaryDone: state.summaryDone || false,
      
      // نقش‌ها
      roleAssignments: state.roleAssignments,
      judgeModel: state.judgeModel,
      summaryModel: state.summaryModel,
      
      // زمان‌ها
      startTime: state.startTime,
      lastUpdate: new Date().toISOString()
    };
    
    const stateJson = JSON.stringify(compactState);
    
    // چک سایز
    if (stateJson.length > 45000) {
      Logger.log('⚠️ State still too large: ' + stateJson.length + ' chars');
      // فقط حداقل ذخیره کن
      const minimalState = {
        promptId: state.promptId,
        status: state.status,
        currentRound: state.currentRound,
        totalRounds: state.totalRounds,
        completedRoundsCount: state.completedRounds?.length || 0
      };
      sheet.getRange('J1').setValue(JSON.stringify(minimalState));
    } else {
      sheet.getRange('J1').setValue(stateJson);
    }
    
    // آپدیت وضعیت کلی
    sheet.getRange('H1').setValue(state.status || STEP_STATUS.RUNNING);
    
    SpreadsheetApp.flush();
    Logger.log('💾 State ذخیره شد در Sheet');
    
  } catch (e) {
    Logger.log('⚠️ خطا در ذخیره state: ' + e);
  }
}

// ========================================
// 📋 JOURNAL SYSTEM - لاگ لحظه‌ای
// ========================================

/**
 * ثبت لاگ در Journal
 */
function logToJournal(promptId, action, details, status) {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    
    // 🔥 چک کردن هر دو نام ممکن
    let journalSheet = ss.getSheetByName('Journal');
    if (!journalSheet) {
      journalSheet = ss.getSheetByName('📋 Journal');
    }
    
    // ایجاد شیت اگر وجود نداشت
    if (!journalSheet) {
      journalSheet = ss.insertSheet('Journal');
      journalSheet.getRange('A1:H1').setValues([['زمان', 'شناسه', 'عملیات', 'جزئیات', 'وضعیت', 'مدت', 'یادداشت', 'اضافی']]);
      journalSheet.getRange('A1:H1').setBackground('#4285f4').setFontColor('white').setFontWeight('bold');
      journalSheet.setFrozenRows(1);
      journalSheet.setColumnWidth(1, 100);
      journalSheet.setColumnWidth(2, 150);
      journalSheet.setColumnWidth(3, 100);
      journalSheet.setColumnWidth(4, 200);
      journalSheet.setColumnWidth(5, 80);
    }
    
    // افزودن ردیف جدید
    const timestamp = Utilities.formatDate(new Date(), 'Asia/Tehran', 'HH:mm:ss');
    const newRow = [
      timestamp,
      promptId ? promptId.substring(3, 18) : '-',
      action || '',
      details ? details.substring(0, 200) : '',
      status || '',
      '',
      '',
      ''
    ];
    
    journalSheet.insertRowAfter(1);
    journalSheet.getRange('A2:H2').setValues([newRow]);
    
    // رنگ‌بندی بر اساس وضعیت
    if (status === '✅') {
      journalSheet.getRange('A2:H2').setBackground('#e6ffe6');
    } else if (status === '❌') {
      journalSheet.getRange('A2:H2').setBackground('#ffe6e6');
    } else if (status === '🔄') {
      journalSheet.getRange('A2:H2').setBackground('#e6f3ff');
    }
    
    // نگه داشتن فقط 500 ردیف آخر
    const lastRow = journalSheet.getLastRow();
    if (lastRow > 500) {
      journalSheet.deleteRows(501, lastRow - 500);
    }
    
  } catch (e) {
    // خطا در Journal نباید پردازش اصلی رو متوقف کنه
    Logger.log('⚠️ Journal error: ' + e);
  }
}

/**
 * بازیابی وضعیت پردازش
 */
function loadWorkSheetState(sheet) {
  try {
    if (!sheet) return null;
    
    const stateJson = sheet.getRange('J1').getValue();
    if (!stateJson) return null;
    
    const state = JSON.parse(stateJson);
    const sheetName = sheet.getName();
    
    Logger.log('📂 بازیابی state از Sheet: دور=' + state.currentRound + ', کل=' + state.totalRounds);
    
    // 🔥 بازسازی completedRounds از جدول پاسخ‌ها (ردیف 34+)
    if (!state.completedRounds || state.completedRounds.length === 0) {
      state.completedRounds = rebuildCompletedRoundsFromWorkSheet(sheet, state);
      Logger.log('📋 بازسازی completedRounds: ' + state.completedRounds.length + ' دور');
    }
    
    // 🔥 بازسازی currentRoundResponses از جدول پاسخ‌ها (ردیف 34+) - نه جدول مدل‌ها!
    const nextRound = (state.currentRound || 0) + 1;
    state.currentRoundResponses = {};
    state.currentRoundTokens = {};
    
    for (let i = 0; i < 50; i++) {
      const row = 34 + i;
      const rowRoundNum = sheet.getRange(`A${row}`).getValue();
      const model = sheet.getRange(`B${row}`).getValue();
      const responsePreview = sheet.getRange(`D${row}`).getValue();
      const tokenCount = sheet.getRange(`F${row}`).getValue();
      const status = sheet.getRange(`H${row}`).getValue();
      
      if (!model || model === '') break;
      
      // فقط پاسخ‌های دور جاری
      if (parseInt(rowRoundNum) === nextRound && status && status.includes('تکمیل')) {
        const fullResponse = readFullResponseFromCache(sheetName, nextRound, model);
        state.currentRoundResponses[model] = fullResponse || responsePreview;
        state.currentRoundTokens[model] = tokenCount || 0;
        Logger.log('📖 پاسخ دور ' + nextRound + ' یافت: ' + model);
      }
    }
    
    Logger.log('📋 پاسخ‌های partial دور ' + nextRound + ': ' + Object.keys(state.currentRoundResponses).length + ' مدل');
    
    return state;
    
  } catch (e) {
    Logger.log('⚠️ خطا در بازیابی state: ' + e);
    return null;
  }
}

/**
 * 🔥 بازسازی completedRounds از جدول پاسخ‌ها
 */
function rebuildCompletedRoundsFromWorkSheet(sheet, state) {
  const completedRounds = [];
  const sheetName = sheet.getName();
  
  Logger.log('🔄 rebuildCompletedRoundsFromWorkSheet از: ' + sheetName);
  
  try {
    // گروه‌بندی پاسخ‌ها بر اساس دور
    const roundsData = {};
    
    // خواندن از جدول پاسخ‌ها (ردیف 34+)
    let foundRows = 0;
    for (let i = 0; i < 50; i++) {
      const row = 34 + i;
      const roundNum = sheet.getRange(`A${row}`).getValue();
      const model = sheet.getRange(`B${row}`).getValue();
      const role = sheet.getRange(`C${row}`).getValue();
      const responsePreview = sheet.getRange(`D${row}`).getValue();
      const tokens = sheet.getRange(`F${row}`).getValue();
      const status = sheet.getRange(`H${row}`).getValue();
      
      if (!model || model === '') {
        Logger.log('📋 پایان جدول پاسخ‌ها در ردیف ' + row);
        break;
      }
      
      foundRows++;
      Logger.log('📖 ردیف ' + row + ': دور=' + roundNum + ', مدل=' + model + ', status=' + status);
      
      // فقط پاسخ‌های تکمیل شده
      if (status && status.includes('تکمیل')) {
        if (!roundsData[roundNum]) {
          roundsData[roundNum] = { responses: {}, tokens: {}, roles: {} };
        }
        
        // خواندن پاسخ کامل از Cache
        const fullResponse = readFullResponseFromCache(sheetName, roundNum, model);
        roundsData[roundNum].responses[model] = fullResponse || responsePreview;
        roundsData[roundNum].tokens[model] = tokens || 0;
        roundsData[roundNum].roles[model] = role || model;
        
        const respLen = (fullResponse || responsePreview || '').length;
        Logger.log('  ✅ پاسخ یافت شد: ' + respLen + ' کاراکتر');
      } else {
        Logger.log('  ⏭️ Skip - status نامعتبر');
      }
    }
    
    Logger.log('📊 ' + foundRows + ' ردیف بررسی شد');
    Logger.log('📊 ' + Object.keys(roundsData).length + ' دور یافت شد');
    
    // تبدیل به آرایه مرتب
    const sortedRounds = Object.keys(roundsData).sort((a, b) => parseInt(a) - parseInt(b));
    for (const roundNum of sortedRounds) {
      const responseCount = Object.keys(roundsData[roundNum].responses).length;
      Logger.log('  📋 دور ' + roundNum + ': ' + responseCount + ' پاسخ');
      
      completedRounds.push({
        round: parseInt(roundNum),
        responses: roundsData[roundNum].responses,
        tokens: roundsData[roundNum].tokens,
        roles: roundsData[roundNum].roles
      });
    }
    
    Logger.log('🔄 بازسازی ' + completedRounds.length + ' دور از جدول پاسخ‌ها');
    
  } catch (e) {
    Logger.log('⚠️ خطا در بازسازی دورها: ' + e);
  }
  
  return completedRounds;
}

/**
 * پیدا کردن Work Sheet یک پردازش
 */
function findWorkSheet(promptId) {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    const idPart = promptId.substring(3, 18);
    
    // اول Work Sheet رو چک کن
    const workSheetName = '🔧 Work_' + idPart;
    let sheet = ss.getSheetByName(workSheetName);
    if (sheet) {
      Logger.log('📋 Work Sheet پیدا شد: ' + workSheetName);
      return sheet;
    }
    
    // اگه نبود، Done Sheet رو چک کن
    const doneSheetName = '✅ Done_' + idPart;
    sheet = ss.getSheetByName(doneSheetName);
    if (sheet) {
      Logger.log('📋 Done Sheet پیدا شد: ' + doneSheetName);
      return sheet;
    }
    
    Logger.log('⚠️ هیچ Sheet برای ' + promptId + ' پیدا نشد');
    return null;
  } catch (e) {
    Logger.log('❌ خطا در findWorkSheet: ' + e);
    return null;
  }
}

/**
 * نهایی کردن Work Sheet
 */
function finalizeWorkSheet(sheet, status) {
  try {
    if (!sheet) return;
    
    // تغییر نام
    const currentName = sheet.getName();
    const newName = currentName.replace('🔧 Work_', '✅ Done_');
    sheet.setName(newName);
    
    // رنگ تب
    sheet.setTabColor(status === 'COMPLETED' ? '#4caf50' : '#f44336');
    
    // وضعیت
    sheet.getRange('H1').setValue(status === 'COMPLETED' ? '✅ تکمیل شده' : '❌ خطا');
    
    SpreadsheetApp.flush();
    
  } catch (e) {
    Logger.log('⚠️ خطا در نهایی کردن: ' + e);
  }
}

// ========================================
// 🎯 SMART SELECTION - انتخاب هوشمند
// ========================================

/**
 * تحلیل محتوا برای انتخاب هوشمند
 */
function analyzeContentForSmartSelection(prompt, attachments) {
  const analysis = {
    hasCode: false,
    hasImage: false,
    hasVideo: false,      // ✅ v17.2: اضافه شد
    hasAudio: false,      // ✅ v17.2: اضافه شد
    hasDocument: false,
    hasData: false,
    isLongContext: false,
    requiresReasoning: false,
    requiresCreativity: false,
    hasDriveLink: false,  // ✅ v17.2: لینک Google Drive
    language: 'fa',
    complexity: 'medium',
    contentTypes: [],
    fileTypes: []
  };
  
  // تحلیل پرامپت
  const promptLower = prompt.toLowerCase();
  
  // ✅ v17.2: تشخیص ویدیو از متن پرامپت
  const videoKeywords = ['ویدیو', 'ویدئو', 'فیلم', 'video', 'mp4', 'avi', 'mov', 'mkv', 'کلیپ', 'clip', 'movie', 'تصویری'];
  analysis.hasVideo = videoKeywords.some(kw => promptLower.includes(kw));
  
  // ✅ v17.2: تشخیص صوت از متن پرامپت
  const audioKeywords = ['صوت', 'صدا', 'audio', 'mp3', 'wav', 'voice', 'پادکست', 'podcast', 'موسیقی', 'music'];
  analysis.hasAudio = audioKeywords.some(kw => promptLower.includes(kw));
  
  // ✅ v17.2: تشخیص لینک Google Drive
  analysis.hasDriveLink = prompt.includes('drive.google.com') || prompt.includes('docs.google.com');
  
  // تشخیص کد
  const codeKeywords = ['کد', 'برنامه', 'تابع', 'function', 'code', 'script', 'debug', 'error', 'bug', 'mql', 'python', 'javascript', 'فانکشن', 'اسکریپت'];
  analysis.hasCode = codeKeywords.some(kw => promptLower.includes(kw));
  
  // تشخیص استدلال
  const reasoningKeywords = ['چرا', 'تحلیل', 'بررسی', 'مقایسه', 'توضیح', 'دلیل', 'analyze', 'explain', 'compare', 'why'];
  analysis.requiresReasoning = reasoningKeywords.some(kw => promptLower.includes(kw));
  
  // تشخیص خلاقیت
  const creativeKeywords = ['خلاقانه', 'ایده', 'طراحی', 'داستان', 'creative', 'design', 'idea', 'story'];
  analysis.requiresCreativity = creativeKeywords.some(kw => promptLower.includes(kw));
  
  // تحلیل فایل‌ها
  if (attachments && attachments.length > 0) {
    attachments.forEach(file => {
      const ext = (file.name || '').split('.').pop().toLowerCase();
      analysis.fileTypes.push(ext);
      
      // کد
      if (['js', 'py', 'java', 'cpp', 'mq5', 'mq4', 'gs', 'ts', 'html', 'css', 'php', 'rb', 'go', 'rs', 'c', 'h', 'hpp'].includes(ext)) {
        analysis.hasCode = true;
        analysis.contentTypes.push('code');
      }
      
      // تصویر
      if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg'].includes(ext)) {
        analysis.hasImage = true;
        analysis.contentTypes.push('image');
      }
      
      // ✅ v17.2: ویدیو
      if (['mp4', 'avi', 'mov', 'mkv', 'wmv', 'webm', 'flv', 'm4v', '3gp'].includes(ext)) {
        analysis.hasVideo = true;
        analysis.contentTypes.push('video');
      }
      
      // ✅ v17.2: صوت
      if (['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a', 'wma'].includes(ext)) {
        analysis.hasAudio = true;
        analysis.contentTypes.push('audio');
      }
      
      // سند
      if (['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt', 'md'].includes(ext)) {
        analysis.hasDocument = true;
        analysis.contentTypes.push('document');
      }
      
      // داده
      if (['csv', 'json', 'xml', 'xlsx', 'xls'].includes(ext)) {
        analysis.hasData = true;
        analysis.contentTypes.push('data');
      }
    });
  }
  
  // طول context
  const totalLength = prompt.length + (attachments || []).reduce((sum, f) => sum + (f.data?.length || 0), 0);
  analysis.isLongContext = totalLength > 50000;
  
  // پیچیدگی
  if (analysis.hasCode && analysis.requiresReasoning) {
    analysis.complexity = 'high';
  } else if (analysis.hasImage || analysis.hasData || analysis.hasVideo) {
    analysis.complexity = 'medium';
  } else {
    analysis.complexity = prompt.length > 500 ? 'medium' : 'low';
  }
  
  // ✅ v17.2: لاگ بهتر برای ویدیو
  if (analysis.hasVideo) {
    Logger.log('🎬 تشخیص ویدیو: پرامپت یا فایل‌ها شامل ویدیو هستند');
  }
  
  Logger.log('📊 تحلیل محتوا: ' + JSON.stringify(analysis));
  
  return analysis;
}

/**
 * انتخاب هوشمند مدل‌ها و تخصیص نقش‌ها
 */
function smartSelectModelsAndRoles(mode, prompt, attachments) {
  Logger.log('\n🎭 === انتخاب هوشمند مدل‌ها و نقش‌ها ===');
  
  // تحلیل محتوا
  const analysis = analyzeContentForSmartSelection(prompt, attachments);
  
  // ✅ v17.2: بررسی دسترسی به Gemini برای محتوای ویدیو/صوت
  const needsVideoAudioSupport = analysis.hasVideo || analysis.hasAudio;
  
  if (needsVideoAudioSupport) {
    Logger.log('🎬 محتوای ویدیو/صوت تشخیص داده شد');
    
    // بررسی آیا حداقل یک مدل Gemini فعال هست
    const geminiModels = Object.keys(MODEL_REGISTRY).filter(id => 
      id.toLowerCase().includes('gemini') && MODEL_REGISTRY[id]?.enabled
    );
    
    if (geminiModels.length === 0) {
      Logger.log('❌ هیچ مدل Gemini فعالی وجود ندارد - ویدیو/صوت قابل پردازش نیست');
      throw new Error('برای پردازش ویدیو یا صوت، حداقل یک مدل Gemini باید فعال باشد. لطفاً در تنظیمات، Gemini را فعال کنید.');
    }
    
    Logger.log('✅ مدل‌های Gemini موجود: ' + geminiModels.join(', '));
  }
  
  // نقش‌های مورد نیاز برای این حالت
  const requiredRoles = MODE_ROLES[mode] || MODE_ROLES.AUTO;
  
  const assignments = [];
  const usedModels = new Set();
  
  // برای هر نقش، بهترین مدل را انتخاب کن
  for (const roleName of requiredRoles) {
    const role = AI_ROLES[roleName];
    if (!role) {
      Logger.log('⚠️ نقش نامعتبر: ' + roleName);
      continue;
    }
    
    // انتخاب بهترین مدل
    let bestModel = null;
    let bestScore = -1;
    
    // ✅ v17.2: اگر ویدیو یا صوت هست، فقط Gemini قابل استفاده است
    const videoAudioOnlyModels = ['gemini-2.0-flash', 'gemini-2.5-pro', 'gemini-2.5-flash'];
    
    if (needsVideoAudioSupport) {
      Logger.log('🎬 فقط Gemini برای این نقش قابل استفاده است');
    }
    
    for (const modelId of Object.keys(MODEL_REGISTRY)) {
      if (usedModels.has(modelId)) continue;
      
      const modelInfo = MODEL_REGISTRY[modelId];
      if (!modelInfo || !modelInfo.enabled || modelInfo.isImageGenerator) continue;
      
      // ✅ v17.2: اگر ویدیو/صوت هست و مدل Gemini نیست، skip کن
      if (needsVideoAudioSupport) {
        const isGemini = modelId.toLowerCase().includes('gemini');
        if (!isGemini) {
          continue; // فقط Gemini میتونه ویدیو/صوت پردازش کنه
        }
      }
      
      let score = 0;
      
      // آیا در لیست ترجیحی است؟
      const preferredIndex = role.bestModels.indexOf(modelId);
      if (preferredIndex >= 0) {
        score += (role.bestModels.length - preferredIndex) * 20;
      }
      
      // قابلیت‌های مورد نیاز
      if (role.capabilities) {
        const hasCapabilities = role.capabilities.every(cap => 
          modelInfo.capabilities && modelInfo.capabilities.includes(cap)
        );
        if (hasCapabilities) score += 30;
      }
      
      // برای کد، مدل‌های coder بهتر
      if (analysis.hasCode && modelId.includes('coder')) score += 25;
      if (analysis.hasCode && modelInfo.capabilities && modelInfo.capabilities.includes('code')) score += 15;
      
      // برای تصویر، مدل‌های vision
      if (analysis.hasImage && modelInfo.supportsImages) score += 30;
      
      // ✅ v17.2: برای ویدیو/صوت، Gemini امتیاز بالا
      if (needsVideoAudioSupport && modelId.toLowerCase().includes('gemini')) {
        score += 100; // امتیاز بالا برای Gemini وقتی ویدیو/صوت هست
        if (modelId.includes('2.0')) score += 30; // Gemini 2.0 بهتر است
        if (modelId.includes('1.5-pro')) score += 20;
      }
      
      // برای context طولانی
      if (analysis.isLongContext && modelInfo.contextWindow > 100000) score += 20;
      
      // اولویت مدل
      score += (5 - (modelInfo.priority || 3)) * 5;
      
      if (score > bestScore) {
        bestScore = score;
        bestModel = modelId;
      }
    }
    
    if (bestModel) {
      usedModels.add(bestModel);
      assignments.push({
        roleName: role.name,
        roleKey: roleName,
        icon: role.icon,
        modelId: bestModel,
        systemPrompt: role.systemPrompt,
        score: bestScore
      });
      
      Logger.log(`  ✅ ${role.icon} ${role.name} → ${bestModel} (امتیاز: ${bestScore})`);
    }
  }
  
  // اگر داور لازم است و هنوز انتخاب نشده
  if (MODES[mode] && MODES[mode].judge) {
    const judgeModel = selectBestJudgeModel(usedModels, needsVideoAudioSupport);
    if (judgeModel) {
      assignments.push({
        roleName: 'داور',
        roleKey: 'JUDGE',
        icon: '⚖️',
        modelId: judgeModel,
        systemPrompt: 'شما داور هستید. بی‌طرفانه قضاوت کنید.',
        isJudge: true
      });
      Logger.log(`  ⚖️ داور → ${judgeModel}`);
    }
  }
  
  // اگر خلاصه‌نویس لازم است
  if (MODES[mode] && MODES[mode].summary) {
    const summaryModel = selectBestSummaryModel(usedModels, needsVideoAudioSupport);
    if (summaryModel) {
      assignments.push({
        roleName: 'خلاصه‌نویس',
        roleKey: 'SUMMARIZER',
        icon: '📝',
        modelId: summaryModel,
        systemPrompt: 'شما خلاصه‌نویس هستید. خلاصه جامع و کامل ارائه دهید.',
        isSummarizer: true
      });
      Logger.log(`  📝 خلاصه‌نویس → ${summaryModel}`);
    }
  }
  
  Logger.log(`🎭 === ${assignments.length} نقش تخصیص داده شد ===\n`);
  
  return {
    assignments: assignments,
    analysis: analysis
  };
}

/**
 * انتخاب مدل داور
 * ✅ v17.2: پشتیبانی از ویدیو
 */
function selectBestJudgeModel(usedModels, hasVideoAudio = false) {
  // ✅ v17.2: اگر ویدیو/صوت هست، Gemini باید داور باشه
  if (hasVideoAudio) {
    const geminiJudges = ['gemini-2.0-flash', 'gemini-2.5-pro', 'gemini-2.5-flash'];
    for (const modelId of geminiJudges) {
      if (MODEL_REGISTRY[modelId]?.enabled) {
        return modelId;
      }
    }
  }
  
  const preferredJudges = ['claude-sonnet-4-20250514', 'gpt-4-turbo', 'gpt-4o'];
  
  for (const modelId of preferredJudges) {
    if (!usedModels.has(modelId) && MODEL_REGISTRY[modelId]?.enabled) {
      return modelId;
    }
  }
  
  // اگر همه استفاده شده‌اند، از یکی مجدد استفاده کن
  return preferredJudges[0];
}

/**
 * انتخاب مدل خلاصه‌نویس
 * ✅ v17.2: پشتیبانی از ویدیو
 */
function selectBestSummaryModel(usedModels, hasVideoAudio = false) {
  // ✅ v17.2: اگر ویدیو/صوت هست، Gemini باید خلاصه‌نویس باشه
  if (hasVideoAudio) {
    const geminiSummarizers = ['gemini-2.0-flash', 'gemini-2.5-flash', 'gemini-2.5-pro'];
    for (const modelId of geminiSummarizers) {
      if (MODEL_REGISTRY[modelId]?.enabled) {
        return modelId;
      }
    }
  }
  
  const preferredSummarizers = ['gemini-2.0-flash', 'claude-3-haiku-20240307', 'gpt-4o-mini'];
  
  for (const modelId of preferredSummarizers) {
    if (!usedModels.has(modelId) && MODEL_REGISTRY[modelId]?.enabled) {
      return modelId;
    }
  }
  
  return preferredSummarizers[0];
}

// وضعیت‌های صف
const QUEUE_STATUS = {
  RUNNING: 'در حال اجرا',
  PAUSED: 'متوقف شده',
  COMPLETED: 'تکمیل شده',
  WAITING_FOLLOWUP: 'منتظر ادامه سوال',
  SATISFIED: 'قانع شده - بسته شده',
  ERROR: 'خطا',
  CANCELLED: 'لغو شده',
  CHUNKED: 'پردازش چند بخشی',  // 🆕
  AUTO_RESUMING: 'ادامه خودکار'  // 🆕
};

// ========================================
// 🔥 CHUNKED PROCESSING SYSTEM
// سیستم پردازش چند بخشی برای فایل‌های بزرگ
// ========================================

const CHUNK_CONFIG = {
  maxChunkSize: 40000,        // حداکثر 40K کاراکتر برای هر chunk
  maxExecutionTime: 240000,   // 4 دقیقه (ms) - زیر 5 دقیقه limit
  autoResumeDelay: 1,         // تاخیر 1 دقیقه برای resume
  maxChunks: 20               // حداکثر 20 بخش
};

// ========================================
// 📝 DRAFT SHEET SYSTEM
// سیستم چرک‌نویس برای پردازش ایمن
// ========================================

/**
 * ایجاد یا دریافت Sheet چرک‌نویس
 */
function getDraftSheet(promptId) {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    const sheetName = '📝 Draft_' + promptId.substring(0, 15);
    
    let sheet = ss.getSheetByName(sheetName);
    
    if (!sheet) {
      sheet = ss.insertSheet(sheetName);
      
      // هدر
      sheet.getRange('A1:J1').setValues([[
        '🔢 ردیف',
        '📄 فایل',
        '📦 بخش',
        '📝 محتوا (خلاصه)',
        '🤖 مدل',
        '💬 پاسخ',
        '✅ وضعیت',
        '❌ خطا',
        '🔧 اصلاح',
        '⏰ زمان'
      ]]);
      
      sheet.getRange('A1:J1')
        .setFontWeight('bold')
        .setBackground('#fbbf24')
        .setFontColor('#000000');
      
      // عرض ستون‌ها
      sheet.setColumnWidth(1, 60);   // ردیف
      sheet.setColumnWidth(2, 150);  // فایل
      sheet.setColumnWidth(3, 80);   // بخش
      sheet.setColumnWidth(4, 200);  // محتوا
      sheet.setColumnWidth(5, 120);  // مدل
      sheet.setColumnWidth(6, 300);  // پاسخ
      sheet.setColumnWidth(7, 100);  // وضعیت
      sheet.setColumnWidth(8, 200);  // خطا
      sheet.setColumnWidth(9, 200);  // اصلاح
      sheet.setColumnWidth(10, 150); // زمان
      
      // Freeze هدر
      sheet.setFrozenRows(1);
      
      Logger.log('📝 Draft Sheet ایجاد شد: ' + sheetName);
    }
    
    return sheet;
    
  } catch (error) {
    Logger.log('❌ خطا در ایجاد Draft Sheet: ' + error);
    return null;
  }
}

/**
 * ثبت یک ردیف در چرک‌نویس
 */
function addDraftRow(sheet, rowData) {
  try {
    const lastRow = sheet.getLastRow();
    const rowNum = lastRow + 1;
    
    const row = [
      rowNum - 1,                                    // ردیف
      rowData.fileName || '-',                       // فایل
      rowData.chunkIndex + '/' + rowData.totalChunks, // بخش
      (rowData.content || '').substring(0, 100) + '...', // محتوا خلاصه
      rowData.model || '-',                          // مدل
      (rowData.response || '').substring(0, 500),    // پاسخ
      rowData.status || '⏳ در انتظار',              // وضعیت
      rowData.error || '',                           // خطا
      rowData.fix || '',                             // اصلاح
      new Date().toLocaleString('fa-IR')             // زمان
    ];
    
    sheet.appendRow(row);
    
    // رنگ‌بندی بر اساس وضعیت
    const statusCell = sheet.getRange(rowNum, 7);
    if (rowData.status === '✅ تایید') {
      statusCell.setBackground('#d1fae5');
    } else if (rowData.status === '❌ خطا') {
      statusCell.setBackground('#fee2e2');
    } else if (rowData.status === '🔧 اصلاح شده') {
      statusCell.setBackground('#fef3c7');
    }
    
    Logger.log(`📝 Draft ردیف ${rowNum - 1} ثبت شد`);
    return rowNum;
    
  } catch (error) {
    Logger.log('⚠️ خطا در ثبت Draft: ' + error);
    return -1;
  }
}

/**
 * آپدیت وضعیت یک ردیف
 */
function updateDraftStatus(sheet, rowNum, status, error, fix) {
  try {
    if (status) sheet.getRange(rowNum, 7).setValue(status);
    if (error) sheet.getRange(rowNum, 8).setValue(error);
    if (fix) sheet.getRange(rowNum, 9).setValue(fix);
    
    // رنگ‌بندی
    const statusCell = sheet.getRange(rowNum, 7);
    if (status === '✅ تایید') {
      statusCell.setBackground('#d1fae5');
    } else if (status === '❌ خطا') {
      statusCell.setBackground('#fee2e2');
    } else if (status === '🔧 اصلاح شده') {
      statusCell.setBackground('#fef3c7');
    }
    
  } catch (error) {
    Logger.log('⚠️ خطا در آپدیت Draft: ' + error);
  }
}

/**
 * ثبت خلاصه نهایی در Draft
 */
function addDraftSummary(sheet, summary) {
  try {
    const lastRow = sheet.getLastRow() + 2;
    
    sheet.getRange(lastRow, 1, 1, 10).merge();
    sheet.getRange(lastRow, 1).setValue('═'.repeat(50) + ' خلاصه نهایی ' + '═'.repeat(50));
    sheet.getRange(lastRow, 1).setFontWeight('bold').setBackground('#e0e7ff');
    
    sheet.getRange(lastRow + 1, 1, 1, 10).merge();
    sheet.getRange(lastRow + 1, 1).setValue(summary.substring(0, 45000));
    
    sheet.getRange(lastRow + 3, 1).setValue('✅ تایید شده: ' + summary.approved);
    sheet.getRange(lastRow + 4, 1).setValue('❌ خطادار: ' + summary.errors);
    sheet.getRange(lastRow + 5, 1).setValue('🔧 اصلاح شده: ' + summary.fixed);
    
  } catch (error) {
    Logger.log('⚠️ خطا در ثبت خلاصه: ' + error);
  }
}

/**
 * انتقال از Draft به Sheet های اصلی
 */
function transferDraftToFinal(promptId) {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    const draftSheetName = '📝 Draft_' + promptId.substring(0, 15);
    const draftSheet = ss.getSheetByName(draftSheetName);
    
    if (!draftSheet) {
      Logger.log('⚠️ Draft Sheet یافت نشد');
      return { success: false, error: 'Draft یافت نشد' };
    }
    
    const data = draftSheet.getDataRange().getValues();
    
    // شمارش
    let approved = 0, errors = 0, fixed = 0;
    const approvedResponses = [];
    
    for (let i = 1; i < data.length; i++) {
      const status = data[i][6];
      const response = data[i][5];
      const model = data[i][4];
      const fix = data[i][8];
      
      if (status === '✅ تایید') {
        approved++;
        approvedResponses.push({ model, response });
      } else if (status === '❌ خطا') {
        errors++;
      } else if (status === '🔧 اصلاح شده') {
        fixed++;
        approvedResponses.push({ model, response: fix || response });
      }
    }
    
    Logger.log(`📊 انتقال: ${approved} تایید, ${errors} خطا, ${fixed} اصلاح`);
    
    // انتقال به Sheet اصلی نتایج
    try {
      let resultsSheet = ss.getSheetByName('نتایج نهایی');
      if (!resultsSheet) {
        resultsSheet = ss.insertSheet('نتایج نهایی');
        resultsSheet.getRange('A1:E1').setValues([['تاریخ', 'ID', 'مدل', 'پاسخ', 'وضعیت']]);
        resultsSheet.getRange('A1:E1').setFontWeight('bold').setBackground('#10b981').setFontColor('#ffffff');
      }
      
      approvedResponses.forEach(r => {
        resultsSheet.appendRow([
          new Date().toLocaleString('fa-IR'),
          promptId,
          r.model,
          r.response.substring(0, 40000),
          '✅'
        ]);
      });
      
      Logger.log('✅ انتقال به Sheet نتایج انجام شد');
      
    } catch (transferError) {
      Logger.log('⚠️ خطا در انتقال: ' + transferError);
    }
    
    // تغییر نام Draft به آرشیو
    try {
      draftSheet.setName('✅ Done_' + promptId.substring(0, 15));
      draftSheet.setTabColor('#10b981');
    } catch (e) {}
    
    return {
      success: true,
      approved: approved,
      errors: errors,
      fixed: fixed,
      total: approved + fixed
    };
    
  } catch (error) {
    Logger.log('❌ خطا در انتقال Draft: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * پاکسازی Draft های قدیمی (بیشتر از 7 روز)
 */
function cleanupOldDrafts() {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    const sheets = ss.getSheets();
    const cutoff = new Date().getTime() - (7 * 24 * 60 * 60 * 1000);
    
    let deleted = 0;
    
    sheets.forEach(sheet => {
      const name = sheet.getName();
      if (name.startsWith('✅ Done_')) {
        // چک کن آیا قدیمی است
        try {
          const lastEdit = sheet.getRange(2, 10).getValue();
          if (lastEdit && new Date(lastEdit).getTime() < cutoff) {
            ss.deleteSheet(sheet);
            deleted++;
          }
        } catch (e) {}
      }
    });
    
    Logger.log(`🧹 ${deleted} Draft قدیمی پاک شد`);
    return deleted;
    
  } catch (error) {
    Logger.log('⚠️ خطا در پاکسازی: ' + error);
    return 0;
  }
}

/**
 * تقسیم متن بزرگ به بخش‌های کوچکتر
 */
function splitIntoChunks(text, maxSize = CHUNK_CONFIG.maxChunkSize) {
  if (!text || text.length <= maxSize) {
    return [text];
  }
  
  const chunks = [];
  let remaining = text;
  let chunkIndex = 0;
  
  while (remaining.length > 0 && chunkIndex < CHUNK_CONFIG.maxChunks) {
    let chunk = remaining.substring(0, maxSize);
    
    // سعی کن در یک breakpoint طبیعی ببر
    if (remaining.length > maxSize) {
      // اول سعی کن در انتهای تابع ببر
      const funcEnd = chunk.lastIndexOf('\n}\n');
      if (funcEnd > maxSize * 0.7) {
        chunk = remaining.substring(0, funcEnd + 3);
      } else {
        // یا در انتهای خط
        const lineEnd = chunk.lastIndexOf('\n');
        if (lineEnd > maxSize * 0.8) {
          chunk = remaining.substring(0, lineEnd + 1);
        }
      }
    }
    
    chunks.push({
      index: chunkIndex,
      content: chunk,
      length: chunk.length,
      processed: false,
      response: null
    });
    
    remaining = remaining.substring(chunk.length);
    chunkIndex++;
  }
  
  Logger.log(`📦 Split into ${chunks.length} chunks`);
  return chunks;
}

/**
 * آماده‌سازی فایل‌ها برای پردازش chunked
 */
function prepareChunkedFiles(attachments) {
  const result = {
    chunks: [],
    totalSize: 0,
    needsChunking: false
  };
  
  for (const file of attachments) {
    let content = '';
    
    try {
      if (file.data) {
        let data = file.data;
        if (data.includes(',')) {
          data = data.split(',')[1];
        }
        content = Utilities.newBlob(Utilities.base64Decode(data)).getDataAsString();
      }
    } catch (e) {
      Logger.log('⚠️ Cannot read file: ' + file.name);
      continue;
    }
    
    result.totalSize += content.length;
    
    if (content.length > CHUNK_CONFIG.maxChunkSize) {
      result.needsChunking = true;
      const fileChunks = splitIntoChunks(content);
      
      fileChunks.forEach((chunk, idx) => {
        result.chunks.push({
          fileName: file.name,
          fileIndex: attachments.indexOf(file),
          chunkIndex: idx,
          totalChunks: fileChunks.length,
          content: chunk.content,
          length: chunk.length,
          processed: false,
          response: null
        });
      });
    } else {
      result.chunks.push({
        fileName: file.name,
        fileIndex: attachments.indexOf(file),
        chunkIndex: 0,
        totalChunks: 1,
        content: content,
        length: content.length,
        processed: false,
        response: null
      });
    }
  }
  
  Logger.log(`📊 Total: ${result.totalSize} chars, ${result.chunks.length} chunks, needsChunking: ${result.needsChunking}`);
  return result;
}

/**
 * ایجاد Trigger برای ادامه خودکار
 */
function createAutoResumeTrigger(promptId) {
  try {
    // حذف trigger های قبلی
    deleteAutoResumeTriggers();
    
    // ذخیره promptId برای trigger
    PropertiesService.getScriptProperties().setProperty('AUTO_RESUME_PROMPT_ID', promptId);
    
    // ایجاد trigger جدید
    ScriptApp.newTrigger('autoResumeProcess')
      .timeBased()
      .after(CHUNK_CONFIG.autoResumeDelay * 60 * 1000) // بعد از 1 دقیقه
      .create();
    
    Logger.log('⏰ Auto-resume trigger created for: ' + promptId);
    return true;
    
  } catch (error) {
    Logger.log('❌ Error creating trigger: ' + error);
    return false;
  }
}

/**
 * حذف trigger های قدیمی
 */
function deleteAutoResumeTriggers() {
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'autoResumeProcess') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
}

/**
 * تابع که توسط Trigger فراخوانی می‌شود
 */
function autoResumeProcess() {
  Logger.log('\n' + '='.repeat(60));
  Logger.log('🔄 AUTO RESUME TRIGGERED');
  Logger.log('='.repeat(60));
  
  try {
    const promptId = PropertiesService.getScriptProperties().getProperty('AUTO_RESUME_PROMPT_ID');
    
    if (!promptId) {
      Logger.log('⚠️ No promptId found for auto-resume');
      deleteAutoResumeTriggers();
      return;
    }
    
    const state = loadState(promptId);
    
    if (!state) {
      Logger.log('⚠️ State not found for: ' + promptId);
      deleteAutoResumeTriggers();
      return;
    }
    
    if (state.status === QUEUE_STATUS.COMPLETED || state.status === QUEUE_STATUS.ERROR) {
      Logger.log('✅ Process already finished');
      deleteAutoResumeTriggers();
      return;
    }
    
    Logger.log('🚀 Resuming chunked process: ' + promptId);
    Logger.log('📊 Current chunk: ' + state.currentChunkIndex + '/' + state.chunks.length);
    
    // ادامه پردازش
    const result = continueChunkedProcess(state);
    
    Logger.log('✅ Auto-resume completed');
    return result;
    
  } catch (error) {
    Logger.log('❌ Auto-resume error: ' + error);
    deleteAutoResumeTriggers();
  }
}

/**
 * شروع پردازش chunked
 */
function startChunkedProcess(prompt, files, models, mode, rounds, judgeModel) {
  Logger.log('\n' + '='.repeat(60));
  Logger.log('🚀 CHUNKED PROCESS START WITH DRAFT SHEET');
  Logger.log('='.repeat(60));
  
  try {
    initialize();
    
    const timestamp = new Date();
    const promptId = 'CHUNK_' + timestamp.getTime();
    
    // 📝 ایجاد Draft Sheet
    const draftSheet = getDraftSheet(promptId);
    if (draftSheet) {
      Logger.log('📝 Draft Sheet آماده است');
    }
    
    // آماده‌سازی chunks
    const chunkedFiles = prepareChunkedFiles(files);
    
    Logger.log('📦 Total chunks: ' + chunkedFiles.chunks.length);
    Logger.log('📏 Total size: ' + chunkedFiles.totalSize + ' chars');
    
    // ثبت اطلاعات اولیه در Draft
    if (draftSheet) {
      addDraftRow(draftSheet, {
        fileName: '🚀 شروع پردازش',
        chunkIndex: 0,
        totalChunks: chunkedFiles.chunks.length,
        content: prompt.substring(0, 100),
        model: models.join(', '),
        response: 'در حال پردازش ' + chunkedFiles.chunks.length + ' بخش...',
        status: '⏳ شروع شد'
      });
    }
    
    // ایجاد state
    const state = {
      promptId: promptId,
      status: QUEUE_STATUS.CHUNKED,
      prompt: prompt,
      originalFiles: files.map(f => ({ name: f.name, mimeType: f.mimeType })),
      chunks: chunkedFiles.chunks,
      currentChunkIndex: 0,
      chunkResponses: [],
      models: models,
      mode: mode,
      rounds: rounds,
      judgeModel: judgeModel,
      startTime: timestamp.toISOString(),
      lastResumeTime: null,
      resumeCount: 0,
      draftStats: { approved: 0, errors: 0, fixed: 0 }
    };
    
    saveState(state);
    
    // شروع پردازش
    return continueChunkedProcess(state);
    
  } catch (error) {
    Logger.log('❌ Chunked process error: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * ادامه پردازش chunked با Draft Sheet
 */
function continueChunkedProcess(state) {
  const startTime = new Date().getTime();
  
  try {
    state.status = QUEUE_STATUS.RUNNING;
    state.lastResumeTime = new Date().toISOString();
    state.resumeCount++;
    
    // 📝 دریافت Draft Sheet
    const draftSheet = getDraftSheet(state.promptId);
    
    Logger.log(`📍 Resume #${state.resumeCount} - Starting from chunk ${state.currentChunkIndex}`);
    
    // پردازش chunks تا زمان مجاز
    while (state.currentChunkIndex < state.chunks.length) {
      const elapsed = new Date().getTime() - startTime;
      
      // بررسی محدودیت زمانی
      if (elapsed > CHUNK_CONFIG.maxExecutionTime) {
        Logger.log(`⏸️ Time limit reached at chunk ${state.currentChunkIndex}`);
        
        // ثبت در Draft
        if (draftSheet) {
          addDraftRow(draftSheet, {
            fileName: '⏸️ توقف موقت',
            chunkIndex: state.currentChunkIndex,
            totalChunks: state.chunks.length,
            content: 'توقف برای جلوگیری از timeout',
            model: '-',
            response: 'ادامه خودکار در 1 دقیقه...',
            status: '⏳ در انتظار ادامه'
          });
        }
        
        state.status = QUEUE_STATUS.AUTO_RESUMING;
        saveState(state);
        
        // ایجاد trigger برای ادامه
        createAutoResumeTrigger(state.promptId);
        
        return {
          success: true,
          paused: true,
          autoResume: true,
          promptId: state.promptId,
          progress: Math.round((state.currentChunkIndex / state.chunks.length) * 100),
          message: `پردازش ${state.currentChunkIndex}/${state.chunks.length} بخش انجام شد. ادامه خودکار در 1 دقیقه...`,
          currentChunk: state.currentChunkIndex,
          totalChunks: state.chunks.length,
          draftStats: state.draftStats
        };
      }
      
      // پردازش chunk فعلی
      const chunk = state.chunks[state.currentChunkIndex];
      Logger.log(`\n📦 Processing chunk ${state.currentChunkIndex + 1}/${state.chunks.length} (${chunk.fileName})`);
      
      const chunkPrompt = buildChunkPrompt(state.prompt, chunk, state.currentChunkIndex, state.chunks.length);
      
      // فراخوانی مدل برای این chunk
      const responses = {};
      let hasError = false;
      let errorMsg = '';
      
      for (const modelId of state.models.slice(0, 2)) { // حداکثر 2 مدل برای سرعت
        try {
          const result = callModel(modelId, chunkPrompt, []);
          responses[modelId] = result.response;
          Logger.log(`  ✅ ${modelId}: ${result.response.length} chars`);
          
          // ✅ ثبت موفقیت در Draft
          if (draftSheet) {
            addDraftRow(draftSheet, {
              fileName: chunk.fileName,
              chunkIndex: state.currentChunkIndex,
              totalChunks: state.chunks.length,
              content: chunk.content,
              model: modelId,
              response: result.response,
              status: '✅ تایید'
            });
            state.draftStats.approved++;
          }
          
        } catch (e) {
          hasError = true;
          errorMsg = e.message;
          responses[modelId] = 'خطا: ' + e.message;
          Logger.log(`  ❌ ${modelId}: ${e.message}`);
          
          // ❌ ثبت خطا در Draft
          if (draftSheet) {
            addDraftRow(draftSheet, {
              fileName: chunk.fileName,
              chunkIndex: state.currentChunkIndex,
              totalChunks: state.chunks.length,
              content: chunk.content,
              model: modelId,
              response: '',
              status: '❌ خطا',
              error: e.message,
              fix: 'نیاز به بررسی دستی یا retry'
            });
            state.draftStats.errors++;
          }
        }
      }
      
      // ذخیره پاسخ chunk
      state.chunkResponses.push({
        chunkIndex: state.currentChunkIndex,
        fileName: chunk.fileName,
        responses: responses,
        hasError: hasError,
        processedAt: new Date().toISOString()
      });
      
      chunk.processed = true;
      state.currentChunkIndex++;
      
      // ذخیره state
      saveState(state);
    }
    
    // همه chunks پردازش شدند - ترکیب نتایج
    Logger.log('\n🎉 All chunks processed! Combining results...');
    
    deleteAutoResumeTriggers();
    
    // ثبت خلاصه در Draft
    if (draftSheet) {
      addDraftSummary(draftSheet, {
        approved: state.draftStats.approved,
        errors: state.draftStats.errors,
        fixed: state.draftStats.fixed
      });
    }
    
    const finalResult = combineChunkResults(state);
    
    // انتقال به Sheet های نهایی
    const transferResult = transferDraftToFinal(state.promptId);
    
    state.status = QUEUE_STATUS.COMPLETED;
    state.finalResult = finalResult;
    state.transferResult = transferResult;
    saveState(state);
    
    return {
      success: true,
      completed: true,
      promptId: state.promptId,
      result: finalResult,
      totalChunks: state.chunks.length,
      resumeCount: state.resumeCount,
      draftStats: state.draftStats,
      transferResult: transferResult,
      message: `پردازش کامل شد! ${state.chunks.length} بخش در ${state.resumeCount} مرحله. تایید: ${state.draftStats.approved}, خطا: ${state.draftStats.errors}`
    };
    
  } catch (error) {
    Logger.log('❌ Chunk process error: ' + error);
    
    // ثبت خطای کلی در Draft
    try {
      const draftSheet = getDraftSheet(state.promptId);
      if (draftSheet) {
        addDraftRow(draftSheet, {
          fileName: '❌ خطای سیستم',
          chunkIndex: state.currentChunkIndex,
          totalChunks: state.chunks.length,
          content: '',
          model: '-',
          response: '',
          status: '❌ خطا',
          error: error.message
        });
      }
    } catch (e) {}
    state.status = QUEUE_STATUS.ERROR;
    state.error = error.message;
    saveState(state);
    deleteAutoResumeTriggers();
    
    return { success: false, error: error.message };
  }
}

/**
 * ساخت prompt برای هر chunk
 */
function buildChunkPrompt(originalPrompt, chunk, currentIndex, totalChunks) {
  return `${originalPrompt}

---
📦 **بخش ${currentIndex + 1} از ${totalChunks}** 
📄 **فایل:** ${chunk.fileName}
${totalChunks > 1 ? '⚠️ این فقط بخشی از فایل است. لطفاً این بخش را تحلیل کنید.' : ''}

\`\`\`
${chunk.content}
\`\`\`

${currentIndex === 0 ? 'لطفاً تحلیل کامل این بخش را ارائه دهید.' : 'این ادامه فایل قبلی است. تحلیل این بخش را اضافه کنید.'}`;
}

/**
 * ترکیب نتایج همه chunks
 */
function combineChunkResults(state) {
  let combined = `# 📊 نتیجه پردازش چند بخشی

📅 **تاریخ:** ${new Date().toLocaleDateString('fa-IR')}
🔢 **تعداد بخش‌ها:** ${state.chunks.length}
🔄 **تعداد resume:** ${state.resumeCount}
🤖 **مدل‌ها:** ${state.models.join(', ')}

---

`;

  // گروه‌بندی پاسخ‌ها بر اساس فایل
  const fileGroups = {};
  state.chunkResponses.forEach(cr => {
    if (!fileGroups[cr.fileName]) {
      fileGroups[cr.fileName] = [];
    }
    fileGroups[cr.fileName].push(cr);
  });
  
  // ساخت خروجی برای هر فایل
  for (const [fileName, chunks] of Object.entries(fileGroups)) {
    combined += `## 📄 ${fileName}\n\n`;
    
    chunks.sort((a, b) => a.chunkIndex - b.chunkIndex);
    
    chunks.forEach(chunk => {
      combined += `### بخش ${chunk.chunkIndex + 1}\n\n`;
      
      for (const [model, response] of Object.entries(chunk.responses)) {
        combined += `**${model.toUpperCase()}:**\n${response.substring(0, 2000)}\n\n`;
      }
      
      combined += '---\n\n';
    });
  }
  
  return combined;
}

/**
 * بررسی نیاز به chunked processing
 */
function needsChunkedProcessing(files) {
  if (!files || files.length === 0) return false;
  
  let totalSize = 0;
  
  for (const file of files) {
    if (file.data) {
      totalSize += file.data.length * 0.75; // تخمین حجم واقعی
    }
  }
  
  // اگر بیشتر از 60K بود، نیاز به chunked processing داریم
  return totalSize > 60000;
}

// پرامپت تفکر عمیق
const THINKING_PROMPT = `شما باید به این سوال پاسخ دهید: {prompt}

لطفاً پاسخ خود را با ساختار زیر ارائه دهید:

### 🧠 فرآیند تفکر من:
[توضیح دهید چطور به این موضوع فکر کردید - مراحل تفکر خود را بنویسید]

### 💡 پاسخ نهایی من:
[پاسخ نهایی و کاربردی شما]

{context}`;

// پرامپت امتیازدهی
const SCORING_PROMPT = `⚠️ مهم: لطفاً کل پاسخ را با دقت کامل بخوانید و سپس امتیاز دهید.

به پاسخ زیر امتیاز بدهید:

**درخواست کاربر:**
{prompt}

**مدل پاسخ‌دهنده:** {targetModel}

**پاسخ کامل:**
{response}

لطفاً بر اساس تمام محتوای پاسخ (نه فقط بخش اول) امتیاز دهید:

1. دقت: [عدد از 25] - آیا پاسخ به سوال/درخواست اصلی پاسخ می‌دهد؟
2. جامعیت: [عدد از 25] - آیا پاسخ کامل است و همه جنبه‌ها را پوشش می‌دهد؟
3. خلاقیت: [عدد از 25] - آیا پاسخ نوآورانه و جالب است؟
4. استدلال: [عدد از 25] - آیا منطق و استدلال قوی دارد؟

امتیاز کل: [مجموع از 100]

مثال فرمت:
1. دقت: 22
2. جامعیت: 24
3. خلاقیت: 20
4. استدلال: 23
امتیاز کل: 89`;

// پرامپت داور - اصلاح شده با {content}
const JUDGE_PROMPT = `شما به عنوان داور این {taskType} عمل می‌کنید.

⚠️ مهم: لطفاً تمام محتوای ارائه شده را با دقت کامل بخوانید و بر اساس کل پاسخ‌ها (نه فقط بخش اول) قضاوت کنید.

**درخواست اصلی کاربر:**
{prompt}

**شرکت‌کنندگان و پاسخ‌های کامل آنها:**
{content}

لطفاً به عنوان یک داور بی‌طرف و با توجه به تمام جزئیات پاسخ‌ها:

### ⚖️ برنده:
[نام مدل برنده]

### 📊 دلیل انتخاب:
[چرا این مدل برنده است - با اشاره به نکات خاص از پاسخ - 3-4 جمله]

### 💡 نقاط قوت برنده:
- [نقطه قوت 1 با مثال از پاسخ]
- [نقطه قوت 2 با مثال از پاسخ]
- [نقطه قوت 3 با مثال از پاسخ]

### ⚠️ نکات برای بهبود سایر شرکت‌کنندگان:
- [برای مدل اول: چه چیزی کم داشت]
- [برای مدل دوم: چه چیزی کم داشت]

### 📋 خلاصه مقایسه:
[مقایسه کوتاه بین پاسخ‌ها - 2-3 جمله]

⚠️ یادآوری: داوری باید عادلانه، بی‌طرفانه و مبتنی بر تمام محتوای ارائه شده باشد.`;

// پرامپت امتیازدهی به داور (با جزئیات)
const JUDGE_SCORING_DETAILED_PROMPT = `داوری زیر را ارزیابی کنید:

موضوع: {prompt}
داور: {judgeModel}
برنده اعلام شده: {winner}
دلیل: {reasoning}

لطفاً با فرمت زیر امتیاز دهید و دلیل کامل بنویسید:

### امتیازات:
1. بی‌طرفی: [عدد از 25]
2. دقت داوری: [عدد از 25]
3. استدلال: [عدد از 25]
4. عدالت: [عدد از 25]

امتیاز کل: [مجموع از 100]

### نقاط قوت داوری:
- [نقطه قوت 1]
- [نقطه قوت 2]

### نقاط ضعف یا اعتراضات:
- [نقطه ضعف یا اعتراض 1]
- [نقطه ضعف یا اعتراض 2]

### دلیل امتیاز:
[توضیح دهید چرا این امتیاز را دادید - 2-3 جمله]`;

// پرامپت خلاصه‌نویس
const SUMMARY_PROMPT = `شما به عنوان خلاصه‌نویس عمل می‌کنید.

**موضوع:** {prompt}
**محتوا:** {allContent}

یک خلاصه جامع بنویسید:
### 📝 خلاصه کلی:
### 🔑 نکات کلیدی:
### 💡 نتیجه‌گیری:`;

// پرامپت ادامه سوال
const FOLLOWUP_PROMPT = `ادامه بحث قبلی:

**موضوع اصلی:** {originalPrompt}
**سوال جدید:** {followupQuestion}

پاسخ دهید:
### 🧠 تفکر:
### 💡 پاسخ:`;


// ========================================
// بخش 1: مقداردهی
// ========================================

function initialize() {
  try {
    Logger.log('✅ سیستم v10.0 FIXED آماده است');
    return true;
  } catch (error) {
    Logger.log('❌ خطا در مقداردهی: ' + error);
    return false;
  }
}

function checkAPIStatus() {
  initialize();
  const keys = getApiKeys();
  return {
    openai: { available: !!keys.openai, model: 'gpt-4-turbo' },
    deepseek: { available: !!keys.deepseek, model: 'deepseek-chat' },
    claude: { available: !!keys.claude, model: 'claude-3-sonnet-20240229' },
    gemini: { available: !!keys.gemini, model: 'gemini-2.0-flash' }
  };
}

// ========================================
// بخش 2: State Management
// ========================================

function createQueueSheet() {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    let sheet = ss.getSheetByName('صف پردازش');
    
    if (!sheet) {
      sheet = ss.insertSheet('صف پردازش');
      sheet.getRange('A1:J1').setValues([[
        'شناسه', 'وضعیت', 'پیشرفت %', 'دور فعلی', 'کل دورها', 
        'مدل فعلی', 'کل مدل‌ها', 'زمان شروع', 'زمان توقف', 'State JSON'
      ]]);
      sheet.getRange('A1:J1').setFontWeight('bold')
        .setBackground('#9333ea').setFontColor('#ffffff');
      
      Logger.log('✅ Sheet "صف پردازش" ایجاد شد');
    }
    
    return sheet;
  } catch (error) {
    Logger.log('❌ خطا در ایجاد صف: ' + error);
    return null;
  }
}

function saveState(state) {
  // 🔥 ساخت state فشرده برای Cache
  const compactState = {
    promptId: state.promptId,
    prompt: state.prompt ? state.prompt.substring(0, 500) : '',
    mode: state.mode,
    status: state.status,
    models: state.models,
    totalRounds: state.totalRounds,
    currentRound: state.currentRound,
    completedRoundsCount: state.completedRounds?.length || 0,
    currentRoundModelsCompleted: state.currentRoundResponses ? Object.keys(state.currentRoundResponses) : [],
    scoringDone: state.scoringDone || false,
    judgeDone: state.judgeDone || false,
    summaryDone: state.summaryDone || false,
    roleAssignments: state.roleAssignments,
    judgeModel: state.judgeModel,
    summaryModel: state.summaryModel,
    startTime: state.startTime,
    lastUpdate: new Date().toISOString()
  };
  
  // 🔥 اول در Cache ذخیره کن (همیشه کار می‌کند)
  try {
    const cache = CacheService.getScriptCache();
    const stateJson = JSON.stringify(compactState);
    cache.put('STATE_' + state.promptId, stateJson, 21600); // 6 ساعت
    Logger.log('💾 State در Cache ذخیره شد: ' + state.promptId);
  } catch (cacheError) {
    Logger.log('⚠️ خطا در Cache: ' + cacheError);
  }
  
  // سپس سعی کن در Sheet هم ذخیره کنی (اختیاری)
  try {
    const sheet = createQueueSheet();
    if (!sheet) {
      Logger.log('⚠️ Sheet در دسترس نیست - فقط Cache استفاده شد');
      return true; // ادامه بده، Cache کافی است
    }
    
    const data = sheet.getDataRange().getValues();
    let rowIndex = -1;
    
    for (let i = 1; i < data.length; i++) {
      if (data[i][0] === state.promptId) {
        rowIndex = i + 1;
        break;
      }
    }
    
    const completedWork = (state.completedRounds?.length || 0) * state.models.length;
    const totalWork = state.totalRounds * state.models.length;
    const progress = Math.round((completedWork / totalWork) * 100);
    
    const row = [
      state.promptId,
      state.status,
      progress + '%',
      (state.currentRound || 0),
      state.totalRounds,
      (state.currentModelIndex || 0),
      state.models.length,
      state.startTime,
      state.pausedAt || '',
      JSON.stringify(compactState)  // 🔥 State فشرده
    ];
    
    if (rowIndex > 0) {
      sheet.getRange(rowIndex, 1, 1, 10).setValues([row]);
    } else {
      sheet.appendRow(row);
    }
    
    Logger.log('📝 State در Sheet ذخیره شد');
    return true;
    
  } catch (error) {
    Logger.log('⚠️ خطا در ذخیره Sheet (Cache موفق بود): ' + error);
    return true; // Cache ذخیره شده، پس ادامه بده
  }
}

function loadState(promptId) {
  // 🔥 اول از Cache بخوان (سریع‌تر)
  try {
    const cache = CacheService.getScriptCache();
    const cached = cache.get('STATE_' + promptId);
    if (cached) {
      const state = JSON.parse(cached);
      Logger.log('📂 State از Cache بارگذاری شد: ' + promptId);
      return state;
    }
  } catch (cacheError) {
    Logger.log('⚠️ خطا در خواندن Cache: ' + cacheError);
  }
  
  // اگر در Cache نبود، از Sheet بخوان
  try {
    const sheet = createQueueSheet();
    if (!sheet) {
      Logger.log('⚠️ Sheet در دسترس نیست');
      return null;
    }
    
    const data = sheet.getDataRange().getValues();
    
    for (let i = 1; i < data.length; i++) {
      if (data[i][0] === promptId) {
        const stateJSON = data[i][9];
        
        // 🔥 بررسی معتبر بودن JSON
        if (!stateJSON || stateJSON === '' || stateJSON === '{}') {
          Logger.log('⚠️ State خالی یا نامعتبر: ' + promptId);
          return null;
        }
        
        try {
          const state = JSON.parse(stateJSON);
          Logger.log('📂 State از Sheet بارگذاری شد: ' + promptId);
          
          // ذخیره در Cache برای دفعات بعد
          try {
            const cache = CacheService.getScriptCache();
            cache.put('STATE_' + promptId, stateJSON, 21600);
          } catch (e) {}
          
          return state;
        } catch (parseError) {
          Logger.log('⚠️ خطا در parse کردن State: ' + parseError);
          Logger.log('  JSON: ' + (stateJSON || '').substring(0, 200));
          return null;
        }
      }
    }
    
    Logger.log('⚠️ State یافت نشد: ' + promptId);
    return null;
  } catch (error) {
    Logger.log('❌ خطا در بارگذاری State: ' + error);
    return null;
  }
}

function deleteState(promptId) {
  try {
    const sheet = createQueueSheet();
    if (!sheet) return false;
    
    const data = sheet.getDataRange().getValues();
    
    for (let i = 1; i < data.length; i++) {
      if (data[i][0] === promptId) {
        sheet.deleteRow(i + 1);
        Logger.log('🗑️ State حذف شد: ' + promptId);
        return true;
      }
    }
    
    return false;
  } catch (error) {
    Logger.log('❌ خطا در حذف State: ' + error);
    return false;
  }
}

function getAllQueueItems() {
  try {
    const sheet = createQueueSheet();
    if (!sheet) return [];
    
    const data = sheet.getDataRange().getValues();
    if (data.length <= 1) return [];
    
    const items = [];
    for (let i = data.length - 1; i >= 1; i--) {
      items.push({
        promptId: data[i][0],
        status: data[i][1],
        progress: data[i][2],
        currentRound: data[i][3],
        totalRounds: data[i][4],
        currentModel: data[i][5],
        totalModels: data[i][6],
        startTime: data[i][7],
        pausedAt: data[i][8]
      });
    }
    
    return items;
  } catch (error) {
    Logger.log('❌ خطا در دریافت صف: ' + error);
    return [];
  }
}

// ========================================
// بخش 3: فراخوانی API - یکپارچه شده
// ========================================

/**
 * تبدیل نام مدل به نام استاندارد
 */
function resolveModelId(modelId) {
  if (MODEL_REGISTRY[modelId]) {
    return modelId;
  }
  if (MODEL_ALIASES[modelId]) {
    return MODEL_ALIASES[modelId];
  }
  // تلاش برای یافتن مدل با نام مشابه
  const lowerModelId = modelId.toLowerCase();
  for (const key of Object.keys(MODEL_REGISTRY)) {
    if (key.toLowerCase().includes(lowerModelId) || lowerModelId.includes(key.toLowerCase())) {
      return key;
    }
  }
  return modelId;
}

/**
 * تشخیص مدل داینامیک از نام آن
 * برای مدل‌هایی که در MODEL_REGISTRY نیستند ولی از OpenRouter یا Groq هستند
 */
function detectDynamicModel(modelId) {
  const keys = getApiKeys();
  
  // الگوهای OpenRouter - معمولاً به فرمت provider/model هستند
  if (modelId.includes('/')) {
    if (keys.openrouter) {
      return {
        provider: 'openrouter',
        name: modelId,
        maxTokens: 4096,
        dynamic: true,
        enabled: true
      };
    }
  }
  
  // الگوهای Groq - مثل llama, mixtral, gemma
  const groqPatterns = ['llama', 'mixtral', 'gemma', 'whisper'];
  const lowerModelId = modelId.toLowerCase();
  
  for (const pattern of groqPatterns) {
    if (lowerModelId.includes(pattern) && keys.groq) {
      return {
        provider: 'groq',
        name: modelId,
        maxTokens: 4096,
        dynamic: true,
        enabled: true
      };
    }
  }
  
  // الگوهای OpenAI - اگه با gpt شروع بشه
  if (lowerModelId.startsWith('gpt') && keys.openai) {
    return {
      provider: 'openai',
      name: modelId,
      maxTokens: 4096,
      dynamic: true,
      enabled: true
    };
  }
  
  // الگوهای Claude - اگه با claude شروع بشه
  if (lowerModelId.startsWith('claude') && keys.claude) {
    return {
      provider: 'claude',
      name: modelId,
      maxTokens: 4096,
      dynamic: true,
      enabled: true
    };
  }
  
  // الگوهای Gemini
  if (lowerModelId.startsWith('gemini') && keys.gemini) {
    return {
      provider: 'gemini',
      name: modelId,
      maxTokens: 4096,
      dynamic: true,
      enabled: true
    };
  }
  
  // اگه OpenRouter کلید داره، همه مدل‌های ناشناخته رو به OpenRouter بفرست
  if (keys.openrouter) {
    return {
      provider: 'openrouter',
      name: modelId,
      maxTokens: 4096,
      dynamic: true,
      enabled: true
    };
  }
  
  return null;
}

/**
 * فراخوانی مدل - نسخه یکپارچه
 */
function callModel(model, prompt, attachments = []) {
  const modelId = resolveModelId(model);
  let modelInfo = MODEL_REGISTRY[modelId];
  
  // اگه مدل در Registry نیست، بررسی کن آیا داینامیک هست
  if (!modelInfo) {
    Logger.log('⚠️ مدل در Registry نیست: ' + model + ' -> ' + modelId);
    
    // تشخیص provider از نام مدل
    const dynamicInfo = detectDynamicModel(modelId);
    if (dynamicInfo) {
      modelInfo = dynamicInfo;
      Logger.log('  🔄 مدل داینامیک شناسایی شد: ' + dynamicInfo.provider);
    } else {
      throw new Error('مدل ناشناخته: ' + model);
    }
  }
  
  // برای مدل‌های داینامیک، enabled رو چک نکن
  if (!modelInfo.dynamic && !modelInfo.enabled) {
    throw new Error('مدل غیرفعال است: ' + modelId);
  }
  
  const apiKey = getApiKey(modelInfo.provider);
  if (!apiKey) {
    throw new Error('کلید API یافت نشد برای: ' + modelInfo.provider);
  }
  
  // 🔥 محدودیت حجم prompt
  let finalPrompt = prompt;
  if (prompt && prompt.length > CONFIG.maxPromptLength) {
    Logger.log('⚠️ Prompt too long: ' + prompt.length + ' → ' + CONFIG.maxPromptLength);
    finalPrompt = prompt.substring(0, CONFIG.maxPromptLength) + '\n\n[... ادامه متن به دلیل حجم زیاد حذف شد ...]';
  }
  
  Logger.log('📞 فراخوانی ' + (modelInfo.name || modelId) + ' (' + modelId + ') از ' + modelInfo.provider);
  Logger.log('📏 Prompt length: ' + finalPrompt.length + ' chars');
  
  let result;
  
  switch(modelInfo.provider) {
    case 'openai':
      result = callOpenAI_Internal(modelId, finalPrompt, attachments, apiKey, modelInfo);
      break;
    case 'claude':
      result = callClaude_Internal(modelId, finalPrompt, attachments, apiKey, modelInfo);
      break;
    case 'deepseek':
      result = callDeepSeek_Internal(modelId, finalPrompt, attachments, apiKey, modelInfo);
      break;
    case 'gemini':
      result = callGemini_Internal(modelId, finalPrompt, attachments, apiKey, modelInfo);
      break;
    case 'openrouter':
      result = callOpenRouter_Internal(modelId, finalPrompt, attachments, apiKey, modelInfo);
      break;
    case 'groq':
      result = callGroq_Internal(modelId, finalPrompt, attachments, apiKey, modelInfo);
      break;
    default:
      throw new Error('Provider ناشناخته: ' + modelInfo.provider);
  }
  
  if (!result.success) {
    throw new Error(result.error || 'خطا در فراخوانی مدل');
  }
  
  // ✅ v17.2: سازگاری با کد قدیمی - برگرداندن response و مدل واقعی
  return {
    response: result.text,
    tokens: result.tokens || 0,
    actualModel: result.model || modelId  // ✅ مدلی که واقعاً پاسخ داد
  };
}

function callOpenAI_Internal(modelId, prompt, attachments, apiKey, modelInfo) {
  try {
    // بررسی آیا مدل DALL-E 3 است (تولید تصویر)
    if (modelId === 'dall-e-3' || modelInfo.isImageGenerator) {
      return callDALLE3(prompt, apiKey);
    }
    
    const endpoint = modelInfo.endpoint;
    
    // استخراج محتوای فایل‌های متنی
    const fileContent = extractFileContent(attachments);
    const fullPrompt = fileContent ? prompt + fileContent : prompt;
    
    const messages = [];
    
    // بررسی تصاویر
    const imageAttachments = attachments.filter(a => a.mimeType && a.mimeType.startsWith('image/'));
    
    if (imageAttachments.length > 0 && modelInfo.supportsImages) {
      const content = [{
        type: 'text',
        text: fullPrompt
      }];
      
      imageAttachments.forEach(file => {
        // تمیز کردن base64 data از prefix
        let imageData = file.data || '';
        if (imageData.includes(',')) {
          imageData = imageData.split(',')[1];
        }
        
        content.push({
          type: 'image_url',
          image_url: {
            url: `data:${file.mimeType};base64,${imageData}`
          }
        });
      });
      
      messages.push({
        role: 'user',
        content: content
      });
    } else {
      messages.push({
        role: 'user',
        content: fullPrompt
      });
    }
    
    const payload = {
      model: modelId,
      messages: messages,
      // 🔧 استفاده از maxTokens مدل به جای CONFIG
      max_tokens: Math.min(CONFIG.maxTokensPerModel, modelInfo.maxTokens || 4096),
      temperature: 0.7
    };
    
    const options = {
      method: 'post',
      contentType: 'application/json',
      headers: {
        'Authorization': 'Bearer ' + apiKey
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };
    
    Logger.log('🚀 Calling OpenAI: ' + modelId);
    const response = UrlFetchApp.fetch(endpoint, options);
    const responseCode = response.getResponseCode();
    
    if (responseCode !== 200) {
      const errorText = response.getContentText();
      Logger.log('❌ OpenAI Error Response: ' + errorText);
      
      // 🆕 ثبت خطا در cache
      if (responseCode === 429) {
        if (errorText.includes('Rate limit') || errorText.includes('TPM')) {
          recordApiError('openai', 'RATE_LIMIT');
        } else if (errorText.includes('too large') || errorText.includes('Requested')) {
          recordApiError('openai', 'INPUT_TOO_LARGE');
        }
      } else if (responseCode === 402 || responseCode === 403) {
        recordApiError('openai', 'BILLING_ERROR');
      }
      
      throw new Error('OpenAI API error: ' + responseCode + ' - ' + errorText.substring(0, 200));
    }
    
    const data = JSON.parse(response.getContentText());
    const text = data.choices[0].message.content;
    
    Logger.log('✅ OpenAI response received: ' + text.length + ' chars');
    
    return {
      success: true,
      text: text,
      model: modelId,
      tokens: data.usage ? data.usage.total_tokens : 0
    };
    
  } catch (error) {
    Logger.log('❌ OpenAI error: ' + error);
    return {
      success: false,
      error: error.toString()
    };
  }
}

function callClaude_Internal(modelId, prompt, attachments, apiKey, modelInfo) {
  try {
    const endpoint = modelInfo.endpoint;
    
    // استخراج محتوای فایل‌های متنی
    const fileContent = extractFileContent(attachments);
    const fullPrompt = fileContent ? prompt + fileContent : prompt;
    
    // بررسی تصاویر
    const imageAttachments = attachments.filter(a => a.mimeType && a.mimeType.startsWith('image/'));
    
    let userContent;
    if (imageAttachments.length > 0) {
      userContent = [
        ...imageAttachments.map(a => {
          // تمیز کردن base64 data از prefix
          let imageData = a.data || '';
          if (imageData.includes(',')) {
            imageData = imageData.split(',')[1];
          }
          return {
            type: 'image',
            source: { type: 'base64', media_type: a.mimeType, data: imageData }
          };
        }),
        { type: 'text', text: fullPrompt }
      ];
    } else {
      userContent = fullPrompt;
    }
    
    const payload = {
      model: modelId,
      // 🔧 استفاده از maxTokens مدل
      max_tokens: Math.min(CONFIG.maxTokensPerModel, modelInfo.maxTokens || 8192),
      messages: [{
        role: 'user',
        content: userContent
      }]
    };
    
    const options = {
      method: 'post',
      contentType: 'application/json',
      headers: {
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01'
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };
    
    Logger.log('🚀 Calling Claude: ' + modelId);
    const response = UrlFetchApp.fetch(endpoint, options);
    const responseCode = response.getResponseCode();
    
    if (responseCode !== 200) {
      const errorText = response.getContentText();
      Logger.log('❌ Claude Error Response: ' + errorText);
      
      // 🆕 ثبت خطا در cache
      if (responseCode === 429) {
        recordApiError('claude', 'RATE_LIMIT');
      } else if (responseCode === 402 || responseCode === 403) {
        recordApiError('claude', 'BILLING_ERROR');
      }
      
      throw new Error('Claude API error: ' + responseCode + ' - ' + errorText.substring(0, 200));
    }
    
    const data = JSON.parse(response.getContentText());
    const text = data.content[0].text;
    
    Logger.log('✅ Claude response received: ' + text.length + ' chars');
    
    return {
      success: true,
      text: text,
      model: modelId,
      tokens: data.usage ? data.usage.input_tokens + data.usage.output_tokens : 0
    };
    
  } catch (error) {
    Logger.log('❌ Claude error: ' + error);
    return {
      success: false,
      error: error.toString()
    };
  }
}

function callDeepSeek_Internal(modelId, prompt, attachments, apiKey, modelInfo) {
  try {
    const endpoint = modelInfo.endpoint;
    
    // استخراج محتوای فایل‌ها
    const fileContent = extractFileContent(attachments);
    const fullPrompt = fileContent ? prompt + fileContent : prompt;
    
    const payload = {
      model: modelId,
      messages: [{ role: 'user', content: fullPrompt }],
      // 🔧 استفاده از maxTokens مدل
      max_tokens: Math.min(CONFIG.maxTokensPerModel, modelInfo.maxTokens || 4096),
      temperature: 0.7
    };
    
    const options = {
      method: 'post',
      contentType: 'application/json',
      headers: {
        'Authorization': 'Bearer ' + apiKey
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };
    
    Logger.log('🚀 Calling DeepSeek: ' + modelId);
    const response = UrlFetchApp.fetch(endpoint, options);
    const responseCode = response.getResponseCode();
    
    if (responseCode !== 200) {
      const errorText = response.getContentText();
      Logger.log('❌ DeepSeek Error Response: ' + errorText);
      
      // 🆕 ثبت خطا در cache
      if (responseCode === 402 || errorText.includes('Insufficient Balance')) {
        recordApiError('deepseek', 'INSUFFICIENT_BALANCE');
      } else if (responseCode === 429) {
        recordApiError('deepseek', 'RATE_LIMIT');
      }
      
      throw new Error('DeepSeek API error: ' + responseCode + ' - ' + errorText.substring(0, 200));
    }
    
    const data = JSON.parse(response.getContentText());
    const text = data.choices[0].message.content;
    
    Logger.log('✅ DeepSeek response received: ' + text.length + ' chars');
    
    return {
      success: true,
      text: text,
      model: modelId,
      tokens: data.usage ? data.usage.total_tokens : 0
    };
    
  } catch (error) {
    Logger.log('❌ DeepSeek error: ' + error);
    return {
      success: false,
      error: error.toString()
    };
  }
}

function callGemini_Internal(modelId, prompt, attachments, apiKey, modelInfo) {
  try {
    // بررسی آیا مدل تصویرساز است
    if (modelInfo.isImageGenerator) {
      return callGeminiImageGeneration(modelId, prompt, apiKey, modelInfo);
    }
    
    const endpoint = modelInfo.endpoint + '?key=' + apiKey;
    
    // استخراج محتوای فایل‌ها
    const fileContent = extractFileContent(attachments);
    let fullPrompt = fileContent ? prompt + fileContent : prompt;
    
    // ✅ v17.2: تشخیص لینک‌های YouTube و Google Drive
    const youtubeUrls = extractYouTubeUrls(fullPrompt);
    const driveUrls = extractGoogleDriveUrls(fullPrompt);
    
    const parts = [];
    
    // ✅ v17.2: پردازش لینک‌های Google Drive
    if (driveUrls.length > 0) {
      Logger.log('📁 تشخیص ' + driveUrls.length + ' لینک Google Drive');
      Logger.log('📝 لینک‌ها: ' + driveUrls.map(d => d.fileId).join(', '));
      
      // محدودیت حجم برای inline_data (20MB)
      const MAX_INLINE_SIZE = 20 * 1024 * 1024;
      let driveFilesProcessed = 0;
      let driveFilesSkipped = 0;
      
      // دانلود و اضافه کردن فایل‌های Drive
      for (let idx = 0; idx < driveUrls.length; idx++) {
        const driveInfo = driveUrls[idx];
        try {
          Logger.log('  📂 تلاش برای دسترسی به فایل: ' + driveInfo.fileId);
          
          const file = DriveApp.getFileById(driveInfo.fileId);
          const fileSize = file.getSize();
          const fileName = file.getName();
          const mimeType = file.getMimeType();
          
          Logger.log('  📥 Drive File ' + (idx + 1) + ': ' + fileName);
          Logger.log('     📊 حجم: ' + (fileSize / (1024 * 1024)).toFixed(2) + 'MB');
          Logger.log('     📄 نوع: ' + mimeType);
          
          // بررسی حجم فایل
          if (fileSize > MAX_INLINE_SIZE) {
            Logger.log('  ⚠️ فایل خیلی بزرگ برای inline_data (' + (fileSize / (1024 * 1024)).toFixed(1) + 'MB > 20MB)');
            
            // تلاش با File API
            try {
              const uploadResult = uploadToGeminiFileAPI(file, apiKey);
              
              if (uploadResult.success) {
                parts.push({
                  fileData: {
                    mimeType: mimeType,
                    fileUri: uploadResult.fileUri
                  }
                });
                Logger.log('  ✅ فایل بزرگ با File API اضافه شد: ' + uploadResult.fileUri);
                driveFilesProcessed++;
              } else {
                Logger.log('  ❌ خطا در File API: ' + uploadResult.error);
                driveFilesSkipped++;
              }
            } catch (uploadError) {
              Logger.log('  ❌ Exception در آپلود: ' + uploadError);
              driveFilesSkipped++;
            }
          } else {
            // فایل کوچک - استفاده از inline_data
            try {
              const blob = file.getBlob();
              const base64 = Utilities.base64Encode(blob.getBytes());
              
              parts.push({
                inlineData: {
                  mimeType: mimeType,
                  data: base64
                }
              });
              Logger.log('  ✅ فایل اضافه شد (inline_data): ' + base64.length + ' bytes');
              driveFilesProcessed++;
            } catch (blobError) {
              Logger.log('  ❌ خطا در خواندن Blob: ' + blobError);
              driveFilesSkipped++;
            }
          }
        } catch (driveError) {
          Logger.log('  ⚠️ خطا در دسترسی به Drive: ' + driveError);
          driveFilesSkipped++;
        }
      }
      
      // گزارش نهایی
      Logger.log('📊 گزارش پردازش Drive: ' + driveFilesProcessed + ' موفق، ' + driveFilesSkipped + ' ناموفق');
      
      // اگر هیچ فایلی پردازش نشد، پیام کمکی اضافه کن
      if (driveFilesProcessed === 0 && driveFilesSkipped > 0) {
        fullPrompt += `

⚠️ **هشدار مهم:** ${driveFilesSkipped} فایل Google Drive تشخیص داده شد اما پردازش نشد.

**دلایل احتمالی:**
1. فایل‌ها بزرگتر از حد مجاز هستند (>20MB برای inline)
2. دسترسی به فایل‌ها امکان‌پذیر نیست
3. فرمت فایل پشتیبانی نمی‌شود

**راه‌حل‌ها:**
- فایل ویدیویی را به چند بخش کوچکتر تقسیم کنید
- یا متن صحبت‌های ویدیو را استخراج و کپی کنید
- یا از ابزار تبدیل صوت به متن استفاده کنید`;
      }
    }
    
    // ✅ v17.2: اگر YouTube بود، هشدار بده
    if (youtubeUrls.length > 0) {
      Logger.log('🎬 تشخیص ' + youtubeUrls.length + ' لینک YouTube');
      Logger.log('⚠️ YouTube مستقیماً پشتیبانی نمی‌شود - نیاز به دانلود و آپلود در Drive');
      
      // اضافه کردن راهنما به پرامپت
      fullPrompt += `

⚠️ **توجه:** لینک(های) YouTube تشخیص داده شد:
${youtubeUrls.map((url, i) => `${i + 1}. ${url}`).join('\n')}

متاسفانه پردازش مستقیم YouTube از طریق API ممکن نیست.
**راه‌حل:** ویدیو را دانلود کرده و در Google Drive آپلود کنید، سپس لینک Drive را استفاده کنید.`;
    }
    
    // اضافه کردن متن پرامپت
    parts.push({ text: fullPrompt });
    
    // اضافه کردن تصاویر آپلود شده
    const imageAttachments = attachments.filter(a => a.mimeType && a.mimeType.startsWith('image/'));
    imageAttachments.forEach(a => {
      // تمیز کردن base64 data از prefix
      let imageData = a.data || '';
      if (imageData.includes(',')) {
        imageData = imageData.split(',')[1];
      }
      parts.push({
        inlineData: { mimeType: a.mimeType, data: imageData }
      });
    });
    
    // ✅ v17.2: اضافه کردن ویدیوهای آپلود شده (base64)
    const videoAttachments = attachments.filter(a => a.mimeType && a.mimeType.startsWith('video/'));
    videoAttachments.forEach(a => {
      let videoData = a.data || '';
      if (videoData.includes(',')) {
        videoData = videoData.split(',')[1];
      }
      parts.push({
        inlineData: { mimeType: a.mimeType, data: videoData }
      });
      Logger.log('📹 Video attachment added: ' + a.name);
    });
    
    const payload = {
      contents: [{ parts: parts }],
      generationConfig: {
        maxOutputTokens: Math.min(CONFIG.maxTokensPerModel, modelInfo.maxTokens || 8192),
        temperature: 0.7
      }
    };
    
    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };
    
    Logger.log('🚀 Calling Gemini: ' + modelId);
    const response = UrlFetchApp.fetch(endpoint, options);
    const responseCode = response.getResponseCode();
    
    if (responseCode !== 200) {
      const errorText = response.getContentText();
      Logger.log('❌ Gemini Error Response: ' + errorText);
      throw new Error('Gemini API error: ' + responseCode + ' - ' + errorText.substring(0, 200));
    }
    
    const data = JSON.parse(response.getContentText());
    
    if (!data.candidates || !data.candidates[0]) {
      throw new Error('پاسخ نامعتبر از Gemini');
    }
    
    const text = data.candidates[0].content.parts[0].text;
    
    Logger.log('✅ Gemini response received: ' + text.length + ' chars');
    
    return {
      success: true,
      text: text,
      model: modelId,
      tokens: data.usageMetadata?.totalTokenCount || 0
    };
    
  } catch (error) {
    Logger.log('❌ Gemini error: ' + error);
    return {
      success: false,
      error: error.toString()
    };
  }
}

/**
 * ✅ v17.2: استخراج لینک‌های YouTube از متن
 */
function extractYouTubeUrls(text) {
  const patterns = [
    /https?:\/\/(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})/g,
    /https?:\/\/youtu\.be\/([a-zA-Z0-9_-]{11})/g,
    /https?:\/\/(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})/g,
    /https?:\/\/(?:www\.)?youtube\.com\/v\/([a-zA-Z0-9_-]{11})/g
  ];
  
  const urls = new Set();
  
  patterns.forEach(pattern => {
    let match;
    while ((match = pattern.exec(text)) !== null) {
      urls.add('https://www.youtube.com/watch?v=' + match[1]);
    }
  });
  
  return Array.from(urls);
}

/**
 * ✅ v17.2: استخراج لینک‌های Google Drive از متن
 */
function extractGoogleDriveUrls(text) {
  const patterns = [
    /https?:\/\/drive\.google\.com\/file\/d\/([a-zA-Z0-9_-]+)/g,
    /https?:\/\/drive\.google\.com\/open\?id=([a-zA-Z0-9_-]+)/g,
    /https?:\/\/docs\.google\.com\/[^\/]+\/d\/([a-zA-Z0-9_-]+)/g
  ];
  
  const files = [];
  const seenIds = new Set();
  
  patterns.forEach(pattern => {
    let match;
    while ((match = pattern.exec(text)) !== null) {
      const fileId = match[1];
      if (!seenIds.has(fileId)) {
        seenIds.add(fileId);
        files.push({
          fileId: fileId,
          url: match[0]
        });
      }
    }
  });
  
  return files;
}

/**
 * ✅ v17.2: آپلود فایل بزرگ به Gemini File API
 * برای فایل‌های بزرگتر از 20MB
 */
function uploadToGeminiFileAPI(driveFile, apiKey) {
  try {
    const fileName = driveFile.getName();
    const mimeType = driveFile.getMimeType();
    const fileSize = driveFile.getSize();
    
    Logger.log('📤 شروع آپلود به Gemini File API: ' + fileName);
    Logger.log('   📊 حجم: ' + (fileSize / (1024 * 1024)).toFixed(2) + 'MB');
    
    // محدودیت Gemini File API: 2GB
    const MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024;
    if (fileSize > MAX_FILE_SIZE) {
      return { success: false, error: 'فایل بزرگتر از 2GB است' };
    }
    
    // گرفتن محتوای فایل
    const blob = driveFile.getBlob();
    const bytes = blob.getBytes();
    
    // مرحله 1: شروع آپلود (Resumable Upload)
    const initUrl = 'https://generativelanguage.googleapis.com/upload/v1beta/files?key=' + apiKey;
    
    const initOptions = {
      method: 'post',
      headers: {
        'X-Goog-Upload-Protocol': 'resumable',
        'X-Goog-Upload-Command': 'start',
        'X-Goog-Upload-Header-Content-Length': fileSize.toString(),
        'X-Goog-Upload-Header-Content-Type': mimeType,
        'Content-Type': 'application/json'
      },
      payload: JSON.stringify({
        file: {
          display_name: fileName
        }
      }),
      muteHttpExceptions: true
    };
    
    const initResponse = UrlFetchApp.fetch(initUrl, initOptions);
    
    if (initResponse.getResponseCode() !== 200) {
      Logger.log('❌ خطا در شروع آپلود: ' + initResponse.getContentText());
      return { success: false, error: 'خطا در شروع آپلود' };
    }
    
    // گرفتن URL آپلود
    const uploadUrl = initResponse.getHeaders()['X-Goog-Upload-URL'] || 
                      initResponse.getHeaders()['x-goog-upload-url'];
    
    if (!uploadUrl) {
      Logger.log('❌ URL آپلود دریافت نشد');
      return { success: false, error: 'URL آپلود دریافت نشد' };
    }
    
    Logger.log('📤 آپلود محتوا...');
    
    // مرحله 2: آپلود محتوا
    const uploadOptions = {
      method: 'post',
      headers: {
        'X-Goog-Upload-Command': 'upload, finalize',
        'X-Goog-Upload-Offset': '0',
        'Content-Type': mimeType
      },
      payload: bytes,
      muteHttpExceptions: true
    };
    
    const uploadResponse = UrlFetchApp.fetch(uploadUrl, uploadOptions);
    
    if (uploadResponse.getResponseCode() !== 200) {
      Logger.log('❌ خطا در آپلود محتوا: ' + uploadResponse.getContentText());
      return { success: false, error: 'خطا در آپلود محتوا' };
    }
    
    const uploadResult = JSON.parse(uploadResponse.getContentText());
    
    if (!uploadResult.file || !uploadResult.file.uri) {
      Logger.log('❌ URI فایل دریافت نشد');
      return { success: false, error: 'URI فایل دریافت نشد' };
    }
    
    const fileUri = uploadResult.file.uri;
    Logger.log('✅ آپلود موفق: ' + fileUri);
    
    // بررسی وضعیت پردازش فایل
    const fileState = uploadResult.file.state;
    if (fileState === 'PROCESSING') {
      Logger.log('⏳ فایل در حال پردازش است...');
      // صبر برای پردازش (حداکثر 60 ثانیه)
      for (let i = 0; i < 12; i++) {
        Utilities.sleep(5000); // 5 ثانیه
        
        const checkUrl = 'https://generativelanguage.googleapis.com/v1beta/' + uploadResult.file.name + '?key=' + apiKey;
        const checkResponse = UrlFetchApp.fetch(checkUrl, { muteHttpExceptions: true });
        
        if (checkResponse.getResponseCode() === 200) {
          const checkResult = JSON.parse(checkResponse.getContentText());
          if (checkResult.state === 'ACTIVE') {
            Logger.log('✅ فایل آماده است');
            break;
          }
        }
        Logger.log('⏳ منتظر پردازش... (' + ((i + 1) * 5) + ' ثانیه)');
      }
    }
    
    return {
      success: true,
      fileUri: fileUri,
      fileName: uploadResult.file.name
    };
    
  } catch (error) {
    Logger.log('❌ خطا در آپلود به File API: ' + error);
    return { success: false, error: error.toString() };
  }
}

/**
 * تولید تصویر با Gemini
 */
function callGeminiImageGeneration(modelId, prompt, apiKey, modelInfo) {
  try {
    Logger.log('🎨 Generating image with: ' + modelId);
    
    // برای Imagen 3
    if (modelId === 'imagen-3') {
      return callImagen3(prompt, apiKey);
    }
    
    // ✅ v17.2: استفاده از endpoint صحیح
    const endpoint = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-preview-image-generation:generateContent?key=' + apiKey;
    
    const payload = {
      contents: [{
        parts: [{ text: prompt }]
      }],
      generationConfig: {
        responseModalities: ['TEXT', 'IMAGE'],
        temperature: 0.8
      }
    };
    
    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };
    
    const response = UrlFetchApp.fetch(endpoint, options);
    const responseCode = response.getResponseCode();
    
    if (responseCode !== 200) {
      const errorText = response.getContentText();
      Logger.log('❌ Gemini Image Gen Error: ' + errorText);
      throw new Error('Image generation error: ' + responseCode);
    }
    
    const data = JSON.parse(response.getContentText());
    
    if (!data.candidates || !data.candidates[0]) {
      throw new Error('پاسخ نامعتبر از Gemini');
    }
    
    const parts = data.candidates[0].content.parts;
    let textResponse = '';
    let imageData = null;
    let imageMimeType = 'image/png';
    
    for (const part of parts) {
      if (part.text) {
        textResponse += part.text;
      }
      if (part.inlineData) {
        imageData = part.inlineData.data;
        imageMimeType = part.inlineData.mimeType || 'image/png';
      }
    }
    
    // ذخیره تصویر در Drive
    let imageUrl = null;
    if (imageData) {
      try {
        const imageBlob = Utilities.newBlob(Utilities.base64Decode(imageData), imageMimeType, 'generated_image.png');
        const folder = getOrCreateFolder('AI_Generated_Images');
        const file = folder.createFile(imageBlob);
        file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
        imageUrl = file.getUrl();
        Logger.log('✅ Image saved to Drive: ' + imageUrl);
      } catch (e) {
        Logger.log('⚠️ Could not save image to Drive: ' + e);
      }
    }
    
    const resultText = imageData 
      ? (textResponse || '🎨 تصویر تولید شد!') + '\n\n📷 [مشاهده تصویر](' + (imageUrl || 'data:' + imageMimeType + ';base64,' + imageData.substring(0, 100) + '...') + ')'
      : textResponse || 'تصویر تولید نشد';
    
    return {
      success: true,
      text: resultText,
      model: modelId,
      tokens: 0,
      hasImage: !!imageData,
      imageUrl: imageUrl,
      imageData: imageData,
      imageMimeType: imageMimeType
    };
    
  } catch (error) {
    Logger.log('❌ Image generation error: ' + error);
    return {
      success: false,
      error: 'خطا در تولید تصویر: ' + error.toString()
    };
  }
}

/**
 * تولید تصویر با Imagen 3
 */
function callImagen3(prompt, apiKey) {
  try {
    Logger.log('🖼️ Generating image with Imagen 3...');
    
    const endpoint = 'https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key=' + apiKey;
    
    const payload = {
      instances: [{ prompt: prompt }],
      parameters: {
        sampleCount: 1,
        aspectRatio: '1:1',
        safetyFilterLevel: 'block_some',
        personGeneration: 'allow_adult'
      }
    };
    
    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };
    
    const response = UrlFetchApp.fetch(endpoint, options);
    const responseCode = response.getResponseCode();
    
    if (responseCode !== 200) {
      const errorText = response.getContentText();
      Logger.log('❌ Imagen 3 Error: ' + errorText);
      
      // اگر Imagen در دسترس نیست، از Gemini استفاده کن
      if (responseCode === 404 || errorText.includes('not found')) {
        Logger.log('⚠️ Imagen 3 not available, falling back to Gemini...');
        return callGeminiImageGeneration('gemini-2.0-flash-preview-image-generation', prompt, apiKey, {isImageGenerator: false});
      }
      
      throw new Error('Imagen 3 error: ' + responseCode);
    }
    
    const data = JSON.parse(response.getContentText());
    
    if (!data.predictions || !data.predictions[0]) {
      throw new Error('پاسخ نامعتبر از Imagen 3');
    }
    
    const imageData = data.predictions[0].bytesBase64Encoded;
    const imageMimeType = 'image/png';
    
    // ذخیره تصویر در Drive
    let imageUrl = null;
    if (imageData) {
      try {
        const imageBlob = Utilities.newBlob(Utilities.base64Decode(imageData), imageMimeType, 'imagen3_' + Date.now() + '.png');
        const folder = getOrCreateFolder('AI_Generated_Images');
        const file = folder.createFile(imageBlob);
        file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
        imageUrl = file.getUrl();
        Logger.log('✅ Imagen 3 image saved: ' + imageUrl);
      } catch (e) {
        Logger.log('⚠️ Could not save Imagen 3 image: ' + e);
      }
    }
    
    return {
      success: true,
      text: '🎨 تصویر با Imagen 3 تولید شد!\n\n📷 [مشاهده تصویر](' + (imageUrl || 'تصویر ذخیره نشد') + ')',
      model: 'imagen-3',
      tokens: 0,
      hasImage: true,
      imageUrl: imageUrl,
      imageData: imageData,
      imageMimeType: imageMimeType
    };
    
  } catch (error) {
    Logger.log('❌ Imagen 3 error: ' + error);
    return {
      success: false,
      error: 'خطا در Imagen 3: ' + error.toString()
    };
  }
}

/**
 * تولید تصویر با DALL-E 3 (OpenAI)
 */
function callDALLE3(prompt, apiKey, options = {}) {
  try {
    Logger.log('🎨 Generating image with DALL-E 3...');
    
    const size = options.size || '1024x1024'; // 1024x1024, 1792x1024, 1024x1792
    const quality = options.quality || 'standard'; // standard, hd
    const style = options.style || 'vivid'; // vivid, natural
    
    const endpoint = 'https://api.openai.com/v1/images/generations';
    
    const payload = {
      model: 'dall-e-3',
      prompt: prompt,
      n: 1,
      size: size,
      quality: quality,
      style: style,
      response_format: 'url' // یا b64_json
    };
    
    const requestOptions = {
      method: 'post',
      headers: {
        'Authorization': 'Bearer ' + apiKey,
        'Content-Type': 'application/json'
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };
    
    const response = UrlFetchApp.fetch(endpoint, requestOptions);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    Logger.log('DALL-E 3 Response Code: ' + responseCode);
    
    if (responseCode !== 200) {
      Logger.log('❌ DALL-E 3 Error: ' + responseText);
      
      // پارس خطا
      try {
        const errorData = JSON.parse(responseText);
        const errorMessage = errorData.error?.message || responseText;
        throw new Error(errorMessage);
      } catch (e) {
        throw new Error('DALL-E 3 error: ' + responseCode + ' - ' + responseText.substring(0, 200));
      }
    }
    
    const data = JSON.parse(responseText);
    
    if (!data.data || !data.data[0]) {
      throw new Error('پاسخ نامعتبر از DALL-E 3');
    }
    
    const imageResult = data.data[0];
    const imageUrl = imageResult.url;
    const revisedPrompt = imageResult.revised_prompt || prompt;
    
    Logger.log('✅ DALL-E 3 image generated: ' + imageUrl);
    Logger.log('📝 Revised prompt: ' + revisedPrompt.substring(0, 100) + '...');
    
    // دانلود و ذخیره تصویر در Drive
    let driveUrl = null;
    let imageData = null;
    try {
      const imageResponse = UrlFetchApp.fetch(imageUrl);
      const imageBlob = imageResponse.getBlob();
      imageData = Utilities.base64Encode(imageBlob.getBytes());
      
      const folder = getOrCreateFolder('AI_Generated_Images');
      const fileName = 'dalle3_' + Date.now() + '.png';
      const file = folder.createFile(imageBlob.setName(fileName));
      file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
      driveUrl = file.getUrl();
      Logger.log('✅ Image saved to Drive: ' + driveUrl);
    } catch (e) {
      Logger.log('⚠️ Could not save image to Drive: ' + e);
    }
    
    const resultText = '🎨 **تصویر با DALL-E 3 تولید شد!**\n\n' +
      '📝 **پرامپت اصلاح شده توسط AI:**\n' + revisedPrompt + '\n\n' +
      '🖼️ **تصویر:**\n' +
      (driveUrl ? '[مشاهده در Google Drive](' + driveUrl + ')' : '[مشاهده تصویر](' + imageUrl + ')') + '\n\n' +
      '⚙️ **تنظیمات:** ' + size + ' | ' + quality + ' | ' + style;
    
    return {
      success: true,
      text: resultText,
      model: 'dall-e-3',
      tokens: 0,
      hasImage: true,
      imageUrl: driveUrl || imageUrl,
      originalUrl: imageUrl,
      imageData: imageData,
      imageMimeType: 'image/png',
      revisedPrompt: revisedPrompt
    };
    
  } catch (error) {
    Logger.log('❌ DALL-E 3 error: ' + error);
    return {
      success: false,
      error: 'خطا در DALL-E 3: ' + error.toString()
    };
  }
}

// ========================================
// 🌐 OpenRouter API - دسترسی به 300+ مدل
// ========================================

function callOpenRouter_Internal(modelId, prompt, attachments, apiKey, modelInfo) {
  try {
    Logger.log('🌐 Calling OpenRouter: ' + modelId);
    
    const endpoint = 'https://openrouter.ai/api/v1/chat/completions';
    
    // استخراج محتوای فایل‌ها
    const fileContent = extractFileContent(attachments);
    const fullPrompt = fileContent ? prompt + fileContent : prompt;
    
    const messages = [{
      role: 'user',
      content: fullPrompt
    }];
    
    const payload = {
      model: modelId,
      messages: messages,
      max_tokens: modelInfo.maxTokens || CONFIG.maxTokensPerModel || 4096,
      temperature: 0.7
    };
    
    const options = {
      method: 'post',
      headers: {
        'Authorization': 'Bearer ' + apiKey,
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://script.google.com',
        'X-Title': 'AI Debate System'
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };
    
    const response = UrlFetchApp.fetch(endpoint, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    Logger.log('  📡 Response code: ' + responseCode);
    
    if (responseCode !== 200) {
      Logger.log('❌ OpenRouter error: ' + responseText);
      const errorData = JSON.parse(responseText);
      throw new Error(errorData.error?.message || 'OpenRouter API error: ' + responseCode);
    }
    
    const data = JSON.parse(responseText);
    
    if (!data.choices || !data.choices[0]) {
      throw new Error('پاسخ نامعتبر از OpenRouter');
    }
    
    const text = data.choices[0].message.content || '';
    const tokens = (data.usage?.total_tokens) || 0;
    
    Logger.log('  ✅ OpenRouter response: ' + text.length + ' chars, ' + tokens + ' tokens');
    
    return {
      success: true,
      text: text,
      model: modelId,
      tokens: tokens,
      provider: 'openrouter'
    };
    
  } catch (error) {
    Logger.log('❌ OpenRouter error: ' + error);
    return {
      success: false,
      error: 'خطا در OpenRouter: ' + error.toString()
    };
  }
}

// ========================================
// ⚡ Groq API - مدل‌های سریع
// ========================================

function callGroq_Internal(modelId, prompt, attachments, apiKey, modelInfo) {
  try {
    Logger.log('⚡ Calling Groq: ' + modelId);
    
    const endpoint = 'https://api.groq.com/openai/v1/chat/completions';
    
    // استخراج محتوای فایل‌ها
    const fileContent = extractFileContent(attachments);
    const fullPrompt = fileContent ? prompt + fileContent : prompt;
    
    const messages = [{
      role: 'user',
      content: fullPrompt
    }];
    
    const payload = {
      model: modelId,
      messages: messages,
      max_tokens: modelInfo.maxTokens || CONFIG.maxTokensPerModel || 4096,
      temperature: 0.7
    };
    
    const options = {
      method: 'post',
      headers: {
        'Authorization': 'Bearer ' + apiKey,
        'Content-Type': 'application/json'
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };
    
    const response = UrlFetchApp.fetch(endpoint, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    Logger.log('  📡 Response code: ' + responseCode);
    
    if (responseCode !== 200) {
      Logger.log('❌ Groq error: ' + responseText);
      const errorData = JSON.parse(responseText);
      throw new Error(errorData.error?.message || 'Groq API error: ' + responseCode);
    }
    
    const data = JSON.parse(responseText);
    
    if (!data.choices || !data.choices[0]) {
      throw new Error('پاسخ نامعتبر از Groq');
    }
    
    const text = data.choices[0].message.content || '';
    const tokens = (data.usage?.total_tokens) || 0;
    
    Logger.log('  ✅ Groq response: ' + text.length + ' chars, ' + tokens + ' tokens');
    
    return {
      success: true,
      text: text,
      model: modelId,
      tokens: tokens,
      provider: 'groq'
    };
    
  } catch (error) {
    Logger.log('❌ Groq error: ' + error);
    return {
      success: false,
      error: 'خطا در Groq: ' + error.toString()
    };
  }
}

// ========================================
// بخش 4: سیستم امتیازدهی
// ========================================

function scoreResponse(scorerModel, targetModel, prompt, targetResponse) {
  try {
    Logger.log(`  📊 ${scorerModel} در حال امتیازدهی به ${targetModel}...`);
    
    // ✅ v17.2: افزایش طول prompt و response برای امتیازدهی دقیق‌تر
    const scoringPrompt = SCORING_PROMPT
      .replace('{prompt}', prompt.substring(0, 1500))        // ✅ از 300 به 1500
      .replace('{targetModel}', targetModel.toUpperCase())
      .replace('{response}', targetResponse.substring(0, 3000)); // ✅ از 1000 به 3000
    
    const originalMax = CONFIG.maxTokensPerModel;
    CONFIG.maxTokensPerModel = CONFIG.maxTokensForScoring;
    
    const result = callModel(scorerModel, scoringPrompt, []);
    
    CONFIG.maxTokensPerModel = originalMax;
    
    const scores = extractScores(result.response);
    
    if (scores.total === 0) {
      Logger.log(`    ⚠️ امتیاز صفر - پاسخ: ${result.response.substring(0, 200)}...`);
    }
    
    Logger.log(`    ✅ امتیاز داده شد: ${scores.total}/100`);
    
    return {
      scorer: scorerModel,
      target: targetModel,
      scores: scores,
      reasoning: result.response,
      tokens: result.tokens
    };
    
  } catch (error) {
    Logger.log(`    ❌ خطا: ${error.message}`);
    return {
      scorer: scorerModel,
      target: targetModel,
      scores: { accuracy: 0, completeness: 0, creativity: 0, reasoning: 0, total: 0 },
      reasoning: 'خطا در امتیازدهی: ' + error.message,
      tokens: 0
    };
  }
}

function extractScores(scoringText) {
  const scores = {
    accuracy: 0,
    completeness: 0,
    creativity: 0,
    reasoning: 0,
    total: 0
  };
  
  try {
    const patterns = {
      accuracy: [
        /دقت.*?(\d+)/i,
        /accuracy.*?(\d+)/i,
        /1\.\s*دقت.*?(\d+)/i,
        /\*\*1\.\s*دقت.*?(\d+)/i
      ],
      completeness: [
        /جامعیت.*?(\d+)/i,
        /completeness.*?(\d+)/i,
        /2\.\s*جامعیت.*?(\d+)/i,
        /\*\*2\.\s*جامعیت.*?(\d+)/i
      ],
      creativity: [
        /خلاقیت.*?(\d+)/i,
        /creativity.*?(\d+)/i,
        /3\.\s*خلاقیت.*?(\d+)/i,
        /\*\*3\.\s*خلاقیت.*?(\d+)/i
      ],
      reasoning: [
        /استدلال.*?(\d+)/i,
        /reasoning.*?(\d+)/i,
        /4\.\s*استدلال.*?(\d+)/i,
        /\*\*4\.\s*استدلال.*?(\d+)/i
      ],
      total: [
        /امتیاز کل.*?(\d+)/i,
        /total.*?(\d+)/i,
        /مجموع.*?(\d+)/i,
        /\*\*امتیاز کل.*?(\d+)/i
      ]
    };
    
    for (const [key, patternList] of Object.entries(patterns)) {
      for (const pattern of patternList) {
        const match = scoringText.match(pattern);
        if (match) {
          const value = parseInt(match[1]);
          scores[key] = Math.min(value, key === 'total' ? 100 : 25);
          break;
        }
      }
    }
    
    if (scores.total === 0) {
      scores.total = Math.min(
        scores.accuracy + scores.completeness + scores.creativity + scores.reasoning,
        100
      );
    }
    
    if (scores.total === 0) {
      const numbers = scoringText.match(/\d+/g);
      if (numbers && numbers.length >= 4) {
        scores.accuracy = Math.min(parseInt(numbers[0]), 25);
        scores.completeness = Math.min(parseInt(numbers[1]), 25);
        scores.creativity = Math.min(parseInt(numbers[2]), 25);
        scores.reasoning = Math.min(parseInt(numbers[3]), 25);
        scores.total = scores.accuracy + scores.completeness + scores.creativity + scores.reasoning;
      }
    }
    
  } catch (error) {
    Logger.log('⚠️ خطا در استخراج امتیازات: ' + error);
  }
  
  return scores;
}

function executeScoring(promptId, prompt, models, roundResults) {
  Logger.log('\n⭐ شروع امتیازدهی...');
  
  const startTime = new Date().getTime();
  const allScores = [];
  const modelAverages = {};
  
  models.forEach(model => {
    modelAverages[model] = [];
  });
  
  const lastRound = roundResults[roundResults.length - 1];
  
  let scoringCount = 0;
  const maxScoringTime = 90;
  
  models.forEach(scorerModel => {
    models.forEach(targetModel => {
      const elapsed = (new Date().getTime() - startTime) / 1000;
      if (elapsed > maxScoringTime) {
        Logger.log(`⚠️ محدودیت زمانی امتیازدهی (${elapsed.toFixed(1)}s) - متوقف شد`);
        return;
      }
      
      if (scorerModel === targetModel) return;
      
      const targetResponse = lastRound.responses[targetModel];
      if (!targetResponse || targetResponse.startsWith('خطا:')) return;
      
      try {
        const scoreResult = scoreResponse(scorerModel, targetModel, prompt, targetResponse);
        allScores.push(scoreResult);
        scoringCount++;
        
        modelAverages[targetModel].push(scoreResult.scores.total);
        
        recordTokenUsage(promptId, scorerModel + '_scoring', scoreResult.tokens);
        
      } catch (error) {
        Logger.log(`⚠️ خطا در امتیازدهی ${scorerModel} به ${targetModel}: ${error.message}`);
      }
    });
  });
  
  const finalScores = {};
  Object.keys(modelAverages).forEach(model => {
    const scores = modelAverages[model];
    if (scores.length > 0) {
      const sum = scores.reduce((a, b) => a + b, 0);
      finalScores[model] = Math.round(sum / scores.length);
    } else {
      finalScores[model] = 0;
    }
  });
  
  const totalTime = (new Date().getTime() - startTime) / 1000;
  Logger.log(`✅ امتیازدهی کامل شد (${totalTime.toFixed(1)}s) - ${scoringCount} امتیاز داده شد`);
  Logger.log('📊 میانگین امتیازات: ' + JSON.stringify(finalScores));
  
  return {
    allScores: allScores,
    averageScores: finalScores,
    scoringTime: totalTime
  };
}

// ========================================
// بخش 5: نقش داور - اصلاح شده
// ========================================

function executeJudging(promptId, prompt, models, judgeModel, roundResults, scoringResult) {
  Logger.log('\n⚖️ شروع داوری...');
  
  try {
    // ✅ v17.2: ساخت محتوای کامل مناظره - بدون truncate شدید
    let debateContent = '';
    const lastRound = roundResults[roundResults.length - 1];
    
    // ✅ v17.2: اضافه کردن پرامپت اصلی برای context کامل
    debateContent += `\n**📋 درخواست اصلی کاربر:**\n${prompt.substring(0, 2000)}\n\n`;
    debateContent += `**پاسخ‌های مدل‌ها:**\n`;
    
    models.forEach(model => {
      if (model === judgeModel) return;
      
      const response = lastRound.responses[model];
      if (!response || response.startsWith('خطا:')) return;
      
      // ✅ v17.2: افزایش به 4000 کاراکتر - کافی برای بررسی واقعی
      debateContent += `\n**${model.toUpperCase()}:**\n${response.substring(0, 4000)}\n`;
    });
    
    if (!debateContent) {
      Logger.log('⚠️ محتوای کافی برای داوری وجود ندارد');
      return null;
    }
    
    // تعیین نوع کار
    const taskType = 'مناظره';
    
    // ✅ v17.2: فراخوانی داور با محتوای کامل‌تر
    const judgePrompt = JUDGE_PROMPT
      .replace('{taskType}', taskType)
      .replace('{prompt}', prompt.substring(0, 2000)) // ✅ افزایش از 300 به 2000
      .replace('{content}', debateContent);
    
    const originalMax = CONFIG.maxTokensPerModel;
    CONFIG.maxTokensPerModel = CONFIG.maxTokensForJudge;
    
    const result = callModel(judgeModel, judgePrompt, []);
    
    CONFIG.maxTokensPerModel = originalMax;
    
    // استخراج نتیجه داوری
    const judgeResult = parseJudgeResponse(result.response);
    
    Logger.log(`✅ داوری کامل شد - برنده: ${judgeResult.winner}`);
    
    // ثبت توکن
    recordTokenUsage(promptId, judgeModel + '_judge', result.tokens);
    
    return {
      judge: judgeModel,
      winner: judgeResult.winner,
      reasoning: judgeResult.reasoning,
      strengths: judgeResult.strengths,
      improvements: judgeResult.improvements,
      fullResponse: result.response,
      tokens: result.tokens
    };
    
  } catch (error) {
    Logger.log('❌ خطا در داوری: ' + error.message);
    return {
      judge: judgeModel,
      winner: 'نامشخص',
      reasoning: 'خطا در داوری: ' + error.message,
      strengths: [],
      improvements: [],
      fullResponse: '',
      tokens: 0
    };
  }
}

function parseJudgeResponse(response) {
  const result = {
    winner: 'نامشخص',
    reasoning: '',
    strengths: [],
    improvements: []
  };
  
  try {
    // استخراج برنده
    const winnerMatch = response.match(/برنده.*?[:：]\s*([^\n]+)/i);
    if (winnerMatch) {
      result.winner = winnerMatch[1].trim();
    }
    
    // استخراج دلیل
    const reasoningMatch = response.match(/دلیل.*?[:：]\s*([^\n]+(?:\n(?!###)[^\n]+)*)/i);
    if (reasoningMatch) {
      result.reasoning = reasoningMatch[1].trim();
    }
    
    // استخراج نقاط قوت
    const strengthsMatch = response.match(/نقاط قوت.*?[:：]([\s\S]*?)(?:###|$)/i);
    if (strengthsMatch) {
      const strengthsText = strengthsMatch[1];
      const strengthsLines = strengthsText.split('\n').filter(l => l.trim().startsWith('-'));
      result.strengths = strengthsLines.map(l => l.replace(/^-\s*/, '').trim());
    }
    
    // استخراج نکات بهبود
    const improvementsMatch = response.match(/نکات.*?بهبود.*?[:：]([\s\S]*?)(?:###|$)/i);
    if (improvementsMatch) {
      const improvementsText = improvementsMatch[1];
      const improvementsLines = improvementsText.split('\n').filter(l => l.trim().startsWith('-'));
      result.improvements = improvementsLines.map(l => l.replace(/^-\s*/, '').trim());
    }
    
  } catch (error) {
    Logger.log('⚠️ خطا در استخراج داوری: ' + error);
  }
  
  return result;
}

function scoreJudgeDetailed(promptId, models, judgeModel, judgeResult, prompt) {
  Logger.log('\n📊 امتیازدهی به داور با جزئیات...');
  
  const allScores = [];
  
  models.forEach(scorerModel => {
    if (scorerModel === judgeModel) return;
    
    try {
      Logger.log(`  📊 ${scorerModel} در حال امتیازدهی به داور ${judgeModel}...`);
      
      const judgeScorePrompt = JUDGE_SCORING_DETAILED_PROMPT
        .replace('{prompt}', prompt.substring(0, 1500))   // ✅ v17.2: از 300 به 1500
        .replace('{judgeModel}', judgeModel.toUpperCase())
        .replace('{winner}', judgeResult.winner)
        .replace('{reasoning}', judgeResult.reasoning);
      
      const originalMax = CONFIG.maxTokensPerModel;
      CONFIG.maxTokensPerModel = 1000;
      
      const result = callModel(scorerModel, judgeScorePrompt, []);
      
      CONFIG.maxTokensPerModel = originalMax;
      
      const details = extractJudgeScoreDetails(result.response);
      
      allScores.push({
        scorer: scorerModel,
        target: judgeModel,
        scores: details.scores,
        strengths: details.strengths,
        weaknesses: details.weaknesses,
        scoreReason: details.scoreReason,
        fullResponse: result.response,
        tokens: result.tokens
      });
      
      Logger.log(`    ✅ امتیاز به داور: ${details.scores.total}/100`);
      
    } catch (error) {
      Logger.log(`    ❌ خطا: ${error.message}`);
    }
  });
  
  let totalScore = 0;
  allScores.forEach(s => totalScore += s.scores.total);
  const averageScore = allScores.length > 0 ? Math.round(totalScore / allScores.length) : 0;
  
  Logger.log(`✅ میانگین امتیاز داور: ${averageScore}/100`);
  
  return {
    allScores: allScores,
    averageScore: averageScore
  };
}

function extractJudgeScoreDetails(response) {
  const details = {
    scores: { neutrality: 0, accuracy: 0, reasoning: 0, fairness: 0, total: 0 },
    strengths: [],
    weaknesses: [],
    scoreReason: ''
  };
  
  try {
    const patterns = {
      neutrality: [/بی‌طرفی.*?(\d+)/i, /1\.\s*بی‌طرفی.*?(\d+)/i],
      accuracy: [/دقت.*?داوری.*?(\d+)/i, /2\.\s*دقت.*?(\d+)/i],
      reasoning: [/استدلال.*?(\d+)/i, /3\.\s*استدلال.*?(\d+)/i],
      fairness: [/عدالت.*?(\d+)/i, /4\.\s*عدالت.*?(\d+)/i],
      total: [/امتیاز کل.*?(\d+)/i, /مجموع.*?(\d+)/i]
    };
    
    for (const [key, patternList] of Object.entries(patterns)) {
      for (const pattern of patternList) {
        const match = response.match(pattern);
        if (match) {
          details.scores[key] = Math.min(parseInt(match[1]), key === 'total' ? 100 : 25);
          break;
        }
      }
    }
    
    if (details.scores.total === 0) {
      details.scores.total = Math.min(
        details.scores.neutrality + details.scores.accuracy + 
        details.scores.reasoning + details.scores.fairness,
        100
      );
    }
    
    const strengthsMatch = response.match(/نقاط قوت.*?[:：]([\s\S]*?)(?:###|نقاط ضعف|$)/i);
    if (strengthsMatch) {
      const strengthsText = strengthsMatch[1];
      const strengthsLines = strengthsText.split('\n').filter(l => l.trim().startsWith('-'));
      details.strengths = strengthsLines.map(l => l.replace(/^-\s*/, '').trim());
    }
    
    const weaknessesMatch = response.match(/نقاط ضعف.*?[:：]([\s\S]*?)(?:###|دلیل|$)/i);
    if (weaknessesMatch) {
      const weaknessesText = weaknessesMatch[1];
      const weaknessesLines = weaknessesText.split('\n').filter(l => l.trim().startsWith('-'));
      details.weaknesses = weaknessesLines.map(l => l.replace(/^-\s*/, '').trim());
    }
    
    const reasonMatch = response.match(/دلیل امتیاز.*?[:：]\s*([^\n]+(?:\n(?!###)[^\n]+)*)/i);
    if (reasonMatch) {
      details.scoreReason = reasonMatch[1].trim();
    }
    
  } catch (error) {
    Logger.log('⚠️ خطا در استخراج جزئیات: ' + error);
  }
  
  return details;
}

// ========================================
// بخش 6: تشخیص خودکار و اجرای دورها
// ========================================

function detectMode(prompt) {
  const lower = prompt.toLowerCase();
  const persianLower = prompt;
  
  const keywords = {
    DEBATE: ['مقایسه', 'بهتر', 'برتر', 'مناظره', 'vs', 'versus', 'کدام', 'چه کسی'],
    COLLABORATION: ['بساز', 'ایجاد', 'طراحی', 'تولید', 'کد', 'برنامه', 'بنویس'],
    DEEP_RESEARCH: ['تحقیق', 'تحلیل', 'بررسی', 'مطالعه', 'جامع', 'کامل'],
    CREATIVE: ['خلاقانه', 'داستان', 'شعر', 'نوآورانه', 'ایده'],
    QUICK: ['چیست', 'چیه', 'تعریف', 'معنی', 'what is', 'define']
  };
  
  let scores = {};
  Object.keys(keywords).forEach(mode => { scores[mode] = 0; });
  
  Object.entries(keywords).forEach(([mode, words]) => {
    words.forEach(word => {
      if (lower.includes(word) || persianLower.includes(word)) {
        scores[mode] += 2;
      }
    });
  });
  
  if (prompt.length < 30) scores.QUICK += 2;
  if (prompt.length > 200) scores.DEEP_RESEARCH += 1;
  
  const maxScore = Math.max(...Object.values(scores));
  const detected = Object.keys(scores).find(k => scores[k] === maxScore) || 'QUICK';
  
  return {
    mode: detected,
    confidence: maxScore > 3 ? 'high' : maxScore > 1 ? 'medium' : 'low',
    scores: scores
  };
}

function executeRound(prompt, attachments, models, roundNum, previousRounds) {
  Logger.log('\n🎯 دور ' + roundNum);
  
  const startTime = new Date().getTime();
  const roundResult = {
    round: roundNum,
    timestamp: new Date().toISOString(),
    responses: {},
    thinking: {},
    tokens: {},
    processingTime: 0
  };
  
  let context = '';
  if (previousRounds.length > 0) {
    context = '\n\n--- پاسخ‌های دورهای قبل ---\n';
    previousRounds.forEach((prev, idx) => {
      context += '\nدور ' + (idx + 1) + ':\n';
      Object.entries(prev.responses).forEach(([m, r]) => {
        // ✅ v17.2: افزایش از 300 به 2000 کاراکتر
        context += m.toUpperCase() + ': ' + r.substring(0, 2000) + (r.length > 2000 ? '...' : '') + '\n';
      });
    });
  }
  
  const fullPrompt = THINKING_PROMPT
    .replace('{prompt}', prompt)
    .replace('{context}', context);
  
  models.forEach(model => {
    try {
      Logger.log('  📞 ' + model + '...');
      
      const result = callModel(model, fullPrompt, attachments);
      const parsed = parseResponse(result.response);
      
      roundResult.responses[model] = parsed.final;
      roundResult.thinking[model] = parsed.thinking;
      roundResult.tokens[model] = result.tokens;
      
      Logger.log('  ✅ ' + model + ' - ' + result.tokens + ' tokens');
      
    } catch (error) {
      Logger.log('  ❌ ' + model + ': ' + error.message);
      roundResult.responses[model] = 'خطا: ' + error.message;
      roundResult.thinking[model] = 'خطا در پردازش';
      roundResult.tokens[model] = 0;
    }
  });
  
  roundResult.processingTime = (new Date().getTime() - startTime) / 1000;
  Logger.log('✅ دور ' + roundNum + ' تکمیل شد (' + roundResult.processingTime.toFixed(1) + 's)');
  
  return roundResult;
}

/**
 * 🔥 اجرای دور با آپدیت لحظه‌ای Work Sheet
 * @param {number} globalStartTime - زمان شروع کل پردازش (برای چک timeout)
 */
function executeRoundWithWorkSheet(prompt, attachments, models, roundNum, previousRounds, state, workSheet, globalStartTime) {
  Logger.log('\n🎯 دور ' + roundNum + ' (با Work Sheet)');
  
  const startTime = new Date().getTime();
  const stepKey = 'ROUND_' + roundNum;
  
  // آپدیت وضعیت: شروع دور
  if (workSheet) {
    updateWorkSheetStep(workSheet, stepKey, STEP_STATUS.RUNNING);
    SpreadsheetApp.flush();
  }
  
  const roundResult = {
    round: roundNum,
    timestamp: new Date().toISOString(),
    responses: {},
    thinking: {},
    tokens: {},
    roles: {},
    processingTime: 0,
    needsPause: false,        // 🔥 آیا نیاز به pause دارد؟
    completedModels: 0        // 🔥 تعداد مدل‌های تکمیل شده
  };
  
  // ساخت context از دورهای قبل
  let context = '';
  if (previousRounds && previousRounds.length > 0) {
    context = '\n\n--- پاسخ‌های دورهای قبل ---\n';
    previousRounds.forEach((prev, idx) => {
      context += '\n🔄 دور ' + (idx + 1) + ':\n';
      Object.entries(prev.responses).forEach(([m, r]) => {
        const role = prev.roles?.[m] || m;
        // ✅ v17.2: افزایش از 500 به 2000 کاراکتر
        context += `${role}: ${r.substring(0, 2000)}${r.length > 2000 ? '...' : ''}\n`;
      });
    });
  }
  
  // استفاده از roleAssignments اگر وجود دارد
  const useRoles = state && state.roleAssignments && state.useSmartRoles;
  const mainRoles = useRoles ? 
    state.roleAssignments.filter(r => !r.isJudge && !r.isSummarizer) : 
    models.map((m, i) => ({ modelId: m, roleName: 'شرکت‌کننده ' + (i+1), icon: '🤖', systemPrompt: '' }));
  
  let modelIndex = 0;
  const totalModels = mainRoles.length;
  
  for (const role of mainRoles) {
    const modelId = role.modelId;
    modelIndex++;
    
    // 🔥 چک timeout قبل از هر مدل!
    const globalElapsed = globalStartTime ? (new Date().getTime() - globalStartTime) / 1000 : 0;
    const remainingTime = CONFIG.pauseThreshold - globalElapsed;
    
    Logger.log(`  ⏱️ زمان گذشته: ${globalElapsed.toFixed(0)}s | باقیمانده: ${remainingTime.toFixed(0)}s`);
    
    // اگر زمان کافی نداریم، pause کن
    if (remainingTime < CONFIG.safetyMargin) {
      Logger.log(`  ⚠️ زمان کافی نیست! Pause قبل از ${role.roleName}`);
      
      roundResult.needsPause = true;
      roundResult.completedModels = modelIndex - 1;
      roundResult.pauseReason = `زمان کافی نیست (${remainingTime.toFixed(0)}s باقیمانده)`;
      
      // آپدیت Work Sheet
      if (workSheet) {
        const modelRow = 6 + modelIndex;
        workSheet.getRange(`E${modelRow}`).setValue('⏸️ در انتظار ادامه');
        workSheet.getRange(`A${modelRow}:H${modelRow}`).setBackground('#ffe0b2');
        updateWorkSheetStep(workSheet, stepKey, STEP_STATUS.PAUSED, `${modelIndex-1}/${totalModels} مدل`);
        SpreadsheetApp.flush();
      }
      
      break; // خروج از loop
    }
    
    try {
      // ✅ v17.2: بهبود لاگینگ برای ردیابی مدل
      Logger.log(`  📞 ${role.icon || '🤖'} ${role.roleName}`);
      Logger.log(`     📍 مدل انتخاب شده: ${modelId}`);
      Logger.log(`     📍 نقش: ${role.roleKey || 'نامشخص'}`);
      
      // آپدیت Work Sheet: شروع این مدل
      if (workSheet) {
        const modelRow = 6 + modelIndex;
        // ✅ v17.2: اضافه کردن نام مدل به worksheet برای ردیابی
        workSheet.getRange(`B${modelRow}`).setValue(modelId);
        workSheet.getRange(`E${modelRow}`).setValue('🔄 در حال پردازش');
        workSheet.getRange(`A${modelRow}:H${modelRow}`).setBackground('#fff9c4');
        SpreadsheetApp.flush();
      }
      
      const modelStart = new Date().getTime();
      
      // ساخت prompt با نقش
      let rolePrompt = '';
      if (role.systemPrompt) {
        rolePrompt = role.systemPrompt + '\n\n---\n\n';
      }
      rolePrompt += THINKING_PROMPT
        .replace('{prompt}', prompt)
        .replace('{context}', context);
      
      // فراخوانی مدل
      const result = callModel(modelId, rolePrompt, attachments);
      const parsed = parseResponse(result.response);
      
      const processingTime = (new Date().getTime() - modelStart) / 1000;
      
      // ✅ v17.2: ثبت مدل واقعی که پاسخ داد
      const actualModel = result.actualModel || modelId;
      if (actualModel !== modelId) {
        Logger.log(`  ⚠️ هشدار: مدل درخواستی ${modelId} اما پاسخ از ${actualModel}`);
      }
      
      roundResult.responses[modelId] = parsed.final;
      roundResult.thinking[modelId] = parsed.thinking;
      roundResult.tokens[modelId] = result.tokens;
      roundResult.roles[modelId] = role.roleName;
      roundResult.completedModels = modelIndex;
      roundResult.actualModels = roundResult.actualModels || {};
      roundResult.actualModels[modelId] = actualModel;
      
      Logger.log(`  ✅ ${role.roleName} (${modelId}): ${parsed.final.length} chars (${processingTime.toFixed(1)}s)`);
      
      // 🔥 آپدیت لحظه‌ای Work Sheet
      if (workSheet) {
        // آپدیت ردیف مدل
        const modelRow = 6 + modelIndex;
        workSheet.getRange(`E${modelRow}`).setValue('✅ تکمیل شده');
        workSheet.getRange(`F${modelRow}`).setValue(result.tokens || 0);
        workSheet.getRange(`G${modelRow}`).setValue(processingTime.toFixed(1) + 's');
        workSheet.getRange(`A${modelRow}:H${modelRow}`).setBackground('#c8e6c9');
        
        // ذخیره پاسخ در بخش پاسخ‌ها
        saveResponseToWorkSheet(workSheet, roundNum, modelId, role.roleName, 
                                parsed.final, result.tokens, processingTime);
        
        SpreadsheetApp.flush();
      }
      
      // ✅ v17.2: اضافه به context برای مدل بعدی با طول کافی
      context += `\n${role.roleName}: ${parsed.final.substring(0, 2000)}${parsed.final.length > 2000 ? '...' : ''}\n`;
      
      // 🔥 چک pause بعد از هر مدل - استراتژی امن
      if (CONFIG.pauseAfterEachModel && modelIndex < totalModels) {
        const globalElapsed = globalStartTime ? (new Date().getTime() - globalStartTime) / 1000 : 0;
        Logger.log(`  ⏱️ بعد از مدل ${modelIndex}: ${globalElapsed.toFixed(0)}s گذشته`);
        
        // اگه بیش از 1 مدل مونده و زمان زیادی گذشته، pause کن
        if (globalElapsed > 60) {  // بعد از 1 دقیقه، pause کن
          Logger.log(`  ⏸️ Pause بعد از مدل ${modelIndex} (${totalModels - modelIndex} مدل باقیمانده)`);
          roundResult.needsPause = true;
          roundResult.pauseReason = `بعد از مدل ${modelIndex} - ${totalModels - modelIndex} مدل باقیمانده`;
          break;
        }
      }
      
    } catch (error) {
      Logger.log(`  ❌ ${role.roleName}: ${error.message}`);
      
      roundResult.responses[modelId] = '❌ خطا: ' + error.message;
      roundResult.thinking[modelId] = 'خطا در پردازش';
      roundResult.tokens[modelId] = 0;
      roundResult.roles[modelId] = role.roleName;
      roundResult.completedModels = modelIndex;
      
      // آپدیت Work Sheet: خطا
      if (workSheet) {
        const modelRow = 6 + modelIndex;
        workSheet.getRange(`E${modelRow}`).setValue('❌ خطا');
        workSheet.getRange(`H${modelRow}`).setValue(error.message.substring(0, 100));
        workSheet.getRange(`A${modelRow}:H${modelRow}`).setBackground('#ffcdd2');
        
        saveResponseToWorkSheet(workSheet, roundNum, modelId, role.roleName,
                                '❌ خطا: ' + error.message, 0, 0);
        
        SpreadsheetApp.flush();
      }
    }
  }
  
  roundResult.processingTime = (new Date().getTime() - startTime) / 1000;
  
  // آپدیت وضعیت: پایان دور
  if (workSheet) {
    updateWorkSheetStep(workSheet, stepKey, STEP_STATUS.DONE, 
      `${Object.keys(roundResult.responses).length} پاسخ (${roundResult.processingTime.toFixed(1)}s)`);
    SpreadsheetApp.flush();
  }
  
  Logger.log(`✅ دور ${roundNum} تکمیل شد (${roundResult.processingTime.toFixed(1)}s)`);
  
  return roundResult;
}

function parseResponse(response) {
  const thinkingMatch = response.match(/###\s*🧠\s*.*?:([\s\S]*?)###\s*💡/);
  const finalMatch = response.match(/###\s*💡\s*.*?:([\s\S]*?)$/);
  
  return {
    thinking: thinkingMatch ? thinkingMatch[1].trim() : 'فرآیند تفکر یافت نشد',
    final: finalMatch ? finalMatch[1].trim() : response
  };
}

function generateConclusion(prompt, allRounds, scoringResult, judgeResult) {
  Logger.log('\n📝 تولید نتیجه‌گیری...');
  
  try {
    let summary = '### 🎯 نتیجه‌گیری نهایی\n\n';
    summary += '**موضوع:** ' + prompt + '\n\n';
    summary += '**تعداد دورها:** ' + allRounds.length + '\n\n';
    
    allRounds.forEach((round, idx) => {
      summary += '#### دور ' + round.round + ':\n';
      Object.entries(round.responses).forEach(([model, response]) => {
        summary += '- **' + model.toUpperCase() + ':** ' + response.substring(0, 200) + '...\n';
      });
      summary += '\n';
    });
    
    if (scoringResult && scoringResult.averageScores) {
      summary += '\n### ⭐ امتیازات:\n';
      Object.entries(scoringResult.averageScores).forEach(([model, score]) => {
        summary += `- **${model.toUpperCase()}:** ${score}/100\n`;
      });
      summary += '\n';
    }
    
    if (judgeResult && judgeResult.winner) {
      summary += '\n### ⚖️ داوری:\n';
      summary += `**برنده:** ${judgeResult.winner}\n`;
      summary += `**دلیل:** ${judgeResult.reasoning}\n\n`;
    }
    
    summary += '\n### ✅ نقاط مشترک:\n';
    summary += 'تمام مدل‌ها در مورد موضوع بحث کردند.\n\n';
    
    summary += '### 🏁 نتیجه:\n';
    summary += 'مناظره/بحث با موفقیت انجام شد.\n';
    
    return summary;
    
  } catch (error) {
    Logger.log('❌ خطا در نتیجه‌گیری: ' + error);
    return '### نتیجه‌گیری\n\nخطا در تولید نتیجه‌گیری.';
  }
}

// ========================================
// بخش 7: ذخیره‌سازی
// ========================================

function saveToSheet_Prompts(promptId, timestamp, prompt, attachments, mode, rounds, models, judgeModel) {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    let sheet = ss.getSheetByName('پرامپت‌ها');
    
    if (!sheet) {
      sheet = ss.insertSheet('پرامپت‌ها');
      sheet.getRange('A1:I1').setValues([[
        'تاریخ', 'ID', 'پرامپت', 'پیوست‌ها', 'حالت', 'دورها', 'مدل‌ها', 'داور', 'وضعیت'
      ]]);
      sheet.getRange('A1:I1').setFontWeight('bold').setBackground('#4facfe').setFontColor('#ffffff');
    }
    
    sheet.appendRow([
      timestamp,
      promptId,
      prompt,
      attachments.map(a => a.name).join(', '),
      MODES[mode] ? MODES[mode].name : mode,
      rounds,
      models.join(', '),
      judgeModel || '-',
      'تکمیل شده'
    ]);
    
    Logger.log('✅ ذخیره در Sheet: پرامپت‌ها');
    
  } catch (error) {
    Logger.log('❌ خطا در ذخیره پرامپت‌ها: ' + error);
  }
}

function saveToSheet_Rounds(promptId, allRounds) {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    let sheet = ss.getSheetByName('دورهای مناظره');
    
    if (!sheet) {
      sheet = ss.insertSheet('دورهای مناظره');
      sheet.getRange('A1:F1').setValues([[
        'ID پرامپت', 'دور', 'تاریخ', 'مدل', 'پاسخ', 'زمان پردازش'
      ]]);
      sheet.getRange('A1:F1').setFontWeight('bold').setBackground('#4facfe').setFontColor('#ffffff');
    }
    
    allRounds.forEach(round => {
      Object.entries(round.responses).forEach(([model, response]) => {
        // 🔥 محدودیت 40K کاراکتر برای هر سلول (زیر 50K limit)
        const truncatedResponse = response.length > 48000 
          ? response.substring(0, 48000) + '\n\n[... متن کوتاه شده ...]' 
          : response;
        
        sheet.appendRow([
          promptId,
          round.round,
          round.timestamp,
          model.toUpperCase(),
          truncatedResponse,
          round.processingTime
        ]);
      });
    });
    
    Logger.log('✅ ذخیره در Sheet: دورهای مناظره');
    
  } catch (error) {
    Logger.log('❌ خطا در ذخیره دورها: ' + error);
  }
}

function saveToSheet_Thinking(promptId, allRounds) {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    let sheet = ss.getSheetByName('فرآیند تفکر');
    
    if (!sheet) {
      sheet = ss.insertSheet('فرآیند تفکر');
      sheet.getRange('A1:F1').setValues([[
        'تاریخ', 'ID پرامپت', 'دور', 'مدل', 'مرحله', 'فرآیند تفکر'
      ]]);
      sheet.getRange('A1:F1').setFontWeight('bold').setBackground('#4facfe').setFontColor('#ffffff');
    }
    
    allRounds.forEach(round => {
      Object.entries(round.thinking).forEach(([model, thinking]) => {
        // 🔥 محدودیت 40K کاراکتر
        const truncatedThinking = thinking.length > 40000 
          ? thinking.substring(0, 40000) + '\n\n[... کوتاه شده ...]' 
          : thinking;
        
        sheet.appendRow([
          new Date().toISOString(),
          promptId,
          round.round,
          model.toUpperCase(),
          'تحلیل و تفکر عمیق',
          truncatedThinking
        ]);
      });
    });
    
    Logger.log('✅ ذخیره در Sheet: فرآیند تفکر');
    
  } catch (error) {
    Logger.log('❌ خطا در ذخیره تفکر: ' + error);
  }
}

function saveToSheet_Tokens(promptId, allRounds) {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    let sheet = ss.getSheetByName('مصرف توکن');
    
    if (!sheet) {
      sheet = ss.insertSheet('مصرف توکن');
      sheet.getRange('A1:E1').setValues([[
        'تاریخ', 'ID پرامپت', 'مدل', 'توکن', 'هزینه تقریبی'
      ]]);
      sheet.getRange('A1:E1').setFontWeight('bold').setBackground('#4facfe').setFontColor('#ffffff');
    }
    
    const costs = {
      'gpt-4-turbo': 0.01 / 1000,
      'gpt-4': 0.03 / 1000,
      'gpt-3.5-turbo': 0.0015 / 1000,
      'deepseek-chat': 0.0014 / 1000,
      'claude-3-opus-20240229': 0.015 / 1000,
      'claude-3-sonnet-20240229': 0.003 / 1000,
      'gemini-2.5-pro': 0.00035 / 1000,
      'gemini-2.5-flash': 0.00001 / 1000
    };
    
    allRounds.forEach(round => {
      Object.entries(round.tokens).forEach(([model, tokens]) => {
        const cost = ((costs[model] || 0.01 / 1000) * tokens).toFixed(6);
        sheet.appendRow([
          new Date().toISOString(),
          promptId,
          model.toUpperCase(),
          tokens,
          '$' + cost
        ]);
      });
    });
    
    Logger.log('✅ ذخیره در Sheet: مصرف توکن');
    
  } catch (error) {
    Logger.log('❌ خطا در ذخیره توکن: ' + error);
  }
}

function saveToSheet_Scores(promptId, scoringResult) {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    let sheet = ss.getSheetByName('امتیازات');
    
    if (!sheet) {
      sheet = ss.insertSheet('امتیازات');
      sheet.getRange('A1:I1').setValues([[
        'تاریخ', 'ID پرامپت', 'امتیازدهنده', 'گیرنده', 'دقت', 'جامعیت', 'خلاقیت', 'استدلال', 'کل'
      ]]);
      sheet.getRange('A1:I1').setFontWeight('bold').setBackground('#f59e0b').setFontColor('#ffffff');
    }
    
    scoringResult.allScores.forEach(score => {
      sheet.appendRow([
        new Date().toISOString(),
        promptId,
        score.scorer.toUpperCase(),
        score.target.toUpperCase(),
        score.scores.accuracy,
        score.scores.completeness,
        score.scores.creativity,
        score.scores.reasoning,
        score.scores.total
      ]);
    });
    
    Logger.log('✅ ذخیره در Sheet: امتیازات');
    
  } catch (error) {
    Logger.log('❌ خطا در ذخیره امتیازات: ' + error);
  }
}

function saveToSheet_Judge(promptId, judgeResult, judgeScores) {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    let sheet = ss.getSheetByName('داوری');
    
    if (!sheet) {
      sheet = ss.insertSheet('داوری');
      sheet.getRange('A1:G1').setValues([[
        'تاریخ', 'ID پرامپت', 'داور', 'برنده', 'دلیل', 'امتیاز داور', 'پاسخ کامل'
      ]]);
      sheet.getRange('A1:G1').setFontWeight('bold').setBackground('#10b981').setFontColor('#ffffff');
    }
    
    sheet.appendRow([
      new Date().toISOString(),
      promptId,
      judgeResult.judge.toUpperCase(),
      judgeResult.winner,
      judgeResult.reasoning,
      judgeScores ? judgeScores.averageScore : 0,
      judgeResult.fullResponse.substring(0, 5000)
    ]);
    
    Logger.log('✅ ذخیره در Sheet: داوری');
    
  } catch (error) {
    Logger.log('❌ خطا در ذخیره داوری: ' + error);
  }
}

function saveToDoc(promptId, timestamp, prompt, mode, allRounds, conclusion, scoringResult, judgeResult) {
  try {
    const doc = DocumentApp.openById(CONFIG.docId);
    const body = doc.getBody();
    
    body.appendParagraph('\n' + '='.repeat(60));
    
    const title = body.appendParagraph(`📊 نتایج مناظره - ${promptId}`);
    title.setHeading(DocumentApp.ParagraphHeading.HEADING1);
    title.setForegroundColor('#4f46e5');
    
    body.appendParagraph(`📅 زمان: ${timestamp}`);
    body.appendParagraph(`🎯 حالت: ${MODES[mode] ? MODES[mode].name : mode}`);
    
    const promptTitle = body.appendParagraph('\n💬 سوال/پرامپت:');
    promptTitle.setHeading(DocumentApp.ParagraphHeading.HEADING2);
    body.appendParagraph(prompt);
    
    body.appendHorizontalRule();
    
    allRounds.forEach(round => {
      const roundTitle = body.appendParagraph(`\n🎯 دور ${round.round}:`);
      roundTitle.setHeading(DocumentApp.ParagraphHeading.HEADING2);
      roundTitle.setForegroundColor('#7c3aed');
      
      Object.entries(round.responses).forEach(([model, response]) => {
        const modelTitle = body.appendParagraph(`\n🤖 ${model.toUpperCase()}:`);
        modelTitle.setHeading(DocumentApp.ParagraphHeading.HEADING3);
        modelTitle.setForegroundColor('#2563eb');
        
        if (round.thinking && round.thinking[model]) {
          const thinkingHeader = body.appendParagraph('🧠 فرآیند تفکر:');
          thinkingHeader.setItalic(true);
          
          body.appendParagraph(round.thinking[model]);
          body.appendParagraph('');
        }
        
        const finalHeader = body.appendParagraph('💡 پاسخ نهایی:');
        finalHeader.setItalic(true);
        
        body.appendParagraph(response);
        body.appendParagraph('');
      });
      
      body.appendHorizontalRule();
    });
    
    if (scoringResult && scoringResult.averageScores) {
      const scoresTitle = body.appendParagraph('\n⭐ امتیازات نهایی');
      scoresTitle.setHeading(DocumentApp.ParagraphHeading.HEADING2);
      scoresTitle.setForegroundColor('#f59e0b');
      
      Object.entries(scoringResult.averageScores).forEach(([model, score]) => {
        body.appendParagraph(`🤖 ${model.toUpperCase()}: ${score}/100`);
      });
      
      body.appendParagraph('');
      body.appendHorizontalRule();
    }
    
    if (judgeResult && judgeResult.winner) {
      const judgeTitle = body.appendParagraph('\n⚖️ داوری');
      judgeTitle.setHeading(DocumentApp.ParagraphHeading.HEADING2);
      judgeTitle.setForegroundColor('#10b981');
      
      body.appendParagraph(`🏆 برنده: ${judgeResult.winner}`);
      body.appendParagraph(`📊 دلیل: ${judgeResult.reasoning}`);
      
      if (judgeResult.strengths && judgeResult.strengths.length > 0) {
        body.appendParagraph('\n💪 نقاط قوت:');
        judgeResult.strengths.forEach(s => {
          body.appendParagraph('  • ' + s);
        });
      }
      
      body.appendParagraph('');
      body.appendHorizontalRule();
    }
    
    const conclusionTitle = body.appendParagraph('\n📊 نتیجه‌گیری');
    conclusionTitle.setHeading(DocumentApp.ParagraphHeading.HEADING2);
    conclusionTitle.setForegroundColor('#10a37f');
    
    body.appendParagraph(conclusion);
    
    doc.saveAndClose();
    Logger.log('✅ ذخیره کامل در Doc');
    
  } catch (error) {
    Logger.log('❌ خطا در ذخیره Doc: ' + error);
  }
}

function recordTokenUsage(promptId, model, tokens) {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    let sheet = ss.getSheetByName('مصرف توکن');
    
    if (!sheet) return;
    
    const costs = {
      'gpt-4-turbo': 0.01 / 1000,
      'gpt-4': 0.03 / 1000,
      'gpt-3.5-turbo': 0.0015 / 1000,
      'deepseek-chat': 0.0014 / 1000,
      'claude-3-sonnet-20240229': 0.003 / 1000,
      'gemini-2.5-pro': 0.00035 / 1000
    };
    
    const baseModel = model.replace('_scoring', '').replace('_judge', '');
    const cost = ((costs[baseModel] || 0.01 / 1000) * tokens).toFixed(6);
    
    sheet.appendRow([
      new Date().toISOString(),
      promptId,
      model.toUpperCase(),
      tokens,
      '$' + cost
    ]);
    
  } catch (error) {
    // Silent fail
  }
}

// ========================================
// بخش 8: توابع اصلی با Queue
// ========================================

function doGet() {
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('سیستم مناظره AI v10.0 FIXED')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function startProcess(prompt, files, models, mode, rounds, judgeModel, summarizerModel) {
  try {
    Logger.log('\n' + '='.repeat(60));
    Logger.log('🚀 شروع فرآیند - v12.0 WORKSHEET');
    Logger.log('='.repeat(60));
    
    initialize();
    
    // Validate prompt
    if (!prompt || !prompt.trim()) {
      throw new Error('پرامپت خالی است');
    }
    
    // ========================================
    // 🌐 تشخیص و استخراج محتوای URL ها
    // ========================================
    let enrichedPrompt = prompt;
    const detectedUrls = extractUrlsFromText(prompt);
    let fetchResults = [];
    
    if (detectedUrls.length > 0) {
      Logger.log('🔗 URL های شناسایی شده: ' + detectedUrls.length);
      
      let urlContents = [];
      let failedUrls = [];
      
      for (const url of detectedUrls.slice(0, 5)) { // حداکثر 5 URL
        Logger.log('  🌐 Fetching: ' + url);
        const fetched = fetchUrlContent(url);
        
        if (fetched.success) {
          urlContents.push({
            url: url,
            title: fetched.title,
            content: fetched.content.substring(0, 20000)
          });
          Logger.log('    ✅ Success: ' + fetched.content.length + ' chars');
          fetchResults.push({ url, success: true, length: fetched.content.length });
        } else {
          Logger.log('    ⚠️ Failed: ' + fetched.error);
          failedUrls.push({
            url: url,
            error: fetched.error,
            isSPA: fetched.isSPA || false,
            suggestion: fetched.suggestion || ''
          });
          fetchResults.push({ url, success: false, error: fetched.error });
        }
      }
      
      // اضافه کردن محتوای موفق به پرامپت
      if (urlContents.length > 0) {
        enrichedPrompt += '\n\n' + '='.repeat(50) + '\n';
        enrichedPrompt += '📎 محتوای لینک‌های استخراج شده:\n';
        enrichedPrompt += '='.repeat(50) + '\n\n';
        
        urlContents.forEach((item, idx) => {
          enrichedPrompt += `### 🔗 لینک ${idx + 1}: ${item.title}\n`;
          enrichedPrompt += `URL: ${item.url}\n\n`;
          enrichedPrompt += `${item.content}\n\n`;
          enrichedPrompt += '-'.repeat(40) + '\n\n';
        });
        
        Logger.log('📝 پرامپت غنی شد با ' + urlContents.length + ' محتوای URL');
      }
      
      // اطلاع‌رسانی درباره لینک‌های ناموفق
      if (failedUrls.length > 0) {
        enrichedPrompt += '\n\n' + '⚠️'.repeat(25) + '\n';
        enrichedPrompt += '⚠️ توجه: برخی لینک‌ها قابل استخراج نبودند:\n';
        enrichedPrompt += '⚠️'.repeat(25) + '\n\n';
        
        failedUrls.forEach((item, idx) => {
          enrichedPrompt += `❌ لینک ${idx + 1}: ${item.url}\n`;
          enrichedPrompt += `   دلیل: ${item.error}\n`;
          if (item.isSPA) {
            enrichedPrompt += `   💡 این یک سایت Single Page Application است. محتوای آن با JavaScript لود می‌شود و قابل استخراج خودکار نیست.\n`;
            enrichedPrompt += `   📋 پیشنهاد: کاربر باید محتوای صفحه را مستقیماً کپی کرده و در پرامپت قرار دهد.\n`;
          }
          enrichedPrompt += '\n';
        });
        
        // پیام راهنما برای مدل‌ها
        enrichedPrompt += '\n📋 راهنما برای مدل‌ها:\n';
        enrichedPrompt += '- اگر محتوای لینکی در دسترس نیست، به کاربر توضیح دهید که چرا.\n';
        enrichedPrompt += '- از کاربر بخواهید محتوا را مستقیماً کپی کند.\n';
        enrichedPrompt += '- سعی نکنید محتوایی که ندارید را حدس بزنید.\n';
      }
    }
    
    // استفاده از پرامپت غنی شده
    prompt = enrichedPrompt;
    
    // آماده‌سازی فایل‌ها
    const attachments = (files || []).map(f => ({
      name: f.name,
      mimeType: f.mimeType,
      data: f.data
    }));
    
    // تبدیل mode به uppercase برای مطابقت با MODES
    const modeUpper = (mode || 'AUTO').toString().toUpperCase();
    
    let finalMode = modeUpper;
    let finalRounds = rounds || 2;
    let detection = null;
    
    if (modeUpper === 'AUTO') {
      detection = detectMode(prompt);
      finalMode = detection.mode;
      finalRounds = MODES[detection.mode].rounds;
      Logger.log('🤖 حالت خودکار: ' + finalMode);
    }
    
    // بررسی وجود mode
    if (!MODES[finalMode]) {
      Logger.log('⚠️ حالت نامعتبر: ' + finalMode + ' - استفاده از COLLABORATION');
      finalMode = 'COLLABORATION';
      finalRounds = MODES.COLLABORATION.rounds;
    }
    
    const timestamp = new Date();
    const promptId = 'AI_' + timestamp.getTime();
    
    Logger.log('📌 ID: ' + promptId);
    Logger.log('🎯 حالت: ' + MODES[finalMode].name);
    Logger.log('🔄 دورها: ' + finalRounds);
    
    // ===== 🎭 بررسی نقش‌دهی هوشمند =====
    const useSmartRoles = !models || models.length === 0 || 
                          (models.length === 1 && models[0] === 'auto');
    
    let roleAssignments = [];
    let contentAnalysis = null;
    
    if (useSmartRoles) {
      Logger.log('🎭 نقش‌دهی هوشمند فعال است');
      
      const selection = smartSelectModelsAndRoles(finalMode, prompt, attachments);
      roleAssignments = selection.assignments;
      contentAnalysis = selection.analysis;
      
      // استخراج مدل‌ها از نقش‌ها
      models = roleAssignments
        .filter(r => !r.isJudge && !r.isSummarizer)
        .map(r => r.modelId);
      
      // داور و خلاصه‌نویس
      const judgeAssignment = roleAssignments.find(r => r.isJudge);
      const summarizerAssignment = roleAssignments.find(r => r.isSummarizer);
      
      if (judgeAssignment) judgeModel = judgeAssignment.modelId;
      if (summarizerAssignment) summarizerModel = summarizerAssignment.modelId;
      
    } else {
      // استفاده از مدل‌های انتخاب شده توسط کاربر
      const uniqueModels = [...new Set(models)];
      if (uniqueModels.length !== models.length) {
        Logger.log('⚠️ مدل‌های تکراری حذف شدند');
      }
      models = uniqueModels;
      
      // ✅ v17.2: بررسی ویدیو/صوت برای مدل‌های دستی
      const promptAnalysis = analyzeContentForSmartSelection(prompt, attachments);
      if (promptAnalysis.hasVideo || promptAnalysis.hasAudio) {
        const hasGemini = models.some(m => m.toLowerCase().includes('gemini'));
        if (!hasGemini) {
          Logger.log('⚠️ ویدیو/صوت تشخیص داده شد اما Gemini انتخاب نشده!');
          
          // اضافه کردن خودکار Gemini به لیست
          const availableGemini = Object.keys(MODEL_REGISTRY).find(id => 
            id.toLowerCase().includes('gemini') && MODEL_REGISTRY[id]?.enabled
          );
          
          if (availableGemini) {
            Logger.log('✅ Gemini خودکار اضافه شد: ' + availableGemini);
            models.unshift(availableGemini); // اضافه به ابتدای لیست
          } else {
            throw new Error('برای پردازش ویدیو یا صوت، حداقل یک مدل Gemini باید فعال باشد.');
          }
        }
        contentAnalysis = promptAnalysis;
      }
      
      // ساخت roleAssignments از مدل‌های کاربر
      roleAssignments = models.map((modelId, idx) => ({
        roleName: 'شرکت‌کننده ' + (idx + 1),
        roleKey: 'PARTICIPANT_' + idx,
        icon: '🤖',
        modelId: modelId,
        systemPrompt: ''
      }));
      
      // اضافه کردن داور و خلاصه‌نویس
      if (judgeModel) {
        roleAssignments.push({
          roleName: 'داور',
          roleKey: 'JUDGE',
          icon: '⚖️',
          modelId: judgeModel,
          isJudge: true
        });
      }
      
      if (summarizerModel) {
        roleAssignments.push({
          roleName: 'خلاصه‌نویس',
          roleKey: 'SUMMARIZER',
          icon: '📝',
          modelId: summarizerModel,
          isSummarizer: true
        });
      }
    }
    
    Logger.log('🤖 مدل‌ها: ' + models.join(', '));
    Logger.log('⚖️ داور: ' + (judgeModel || 'ندارد'));
    Logger.log('📝 پرامپت: ' + prompt.substring(0, 100) + '...');
    
    // ===== 📋 ایجاد Work Sheet =====
    let workSheet = null;
    try {
      workSheet = createWorkSheet(promptId, prompt, finalMode, attachments);
      updateWorkSheetStep(workSheet, 'INIT', STEP_STATUS.RUNNING);
      updateWorkSheetStep(workSheet, 'ANALYZE_CONTENT', STEP_STATUS.RUNNING);
      
      if (contentAnalysis) {
        updateWorkSheetStep(workSheet, 'ANALYZE_CONTENT', STEP_STATUS.DONE, 
          JSON.stringify(contentAnalysis).substring(0, 100));
      } else {
        updateWorkSheetStep(workSheet, 'ANALYZE_CONTENT', STEP_STATUS.DONE, 'تحلیل کاربر');
      }
      
      updateWorkSheetStep(workSheet, 'SELECT_MODELS', STEP_STATUS.DONE, models.length + ' مدل');
      updateWorkSheetStep(workSheet, 'ASSIGN_ROLES', STEP_STATUS.DONE, 
        roleAssignments.map(r => r.roleName).join(', '));
      updateWorkSheetStep(workSheet, 'PREPARE_FILES', STEP_STATUS.DONE, attachments.length + ' فایل');
      updateWorkSheetStep(workSheet, 'INIT', STEP_STATUS.DONE);
      
      // ذخیره مدل‌ها در Work Sheet
      saveModelsToWorkSheet(workSheet, roleAssignments);
      
    } catch (wsError) {
      Logger.log('⚠️ خطا در ایجاد Work Sheet: ' + wsError);
      // ادامه بدون Work Sheet
    }
    
    // 🔥 سیستم Chunked Processing غیرفعال شده - برای فایل‌های بزرگ، محتوا truncate میشه
    // if (needsChunkedProcessing(attachments)) {
    //   Logger.log('📦 فایل‌های بزرگ تشخیص داده شدند - استفاده از پردازش چند بخشی');
    //   return startChunkedProcess(prompt, attachments, models, mode, rounds, judgeModel);
    // }
    
    // 🔥 برای فایل‌های بزرگ، محتوا رو محدود میکنیم
    let processedAttachments = attachments || [];
    if (processedAttachments.length > 0) {
      const MAX_CONTENT_LENGTH = 30000; // حداکثر 30K کاراکتر برای هر فایل
      processedAttachments = processedAttachments.map(file => {
        if (file.content && file.content.length > MAX_CONTENT_LENGTH) {
          Logger.log('📏 فایل ' + file.name + ' truncate شد: ' + file.content.length + ' → ' + MAX_CONTENT_LENGTH);
          return {
            ...file,
            content: file.content.substring(0, MAX_CONTENT_LENGTH) + '\n\n... [ادامه فایل به دلیل حجم بالا حذف شد] ...',
            originalLength: file.content.length,
            truncated: true
          };
        }
        return file;
      });
    }
    
    // ایجاد State اولیه
    const state = {
      promptId: promptId,
      status: QUEUE_STATUS.RUNNING,
      prompt: prompt,
      attachments: processedAttachments,  // 🔥 استفاده از نسخه truncate شده
      mode: finalMode,
      models: models,
      judgeModel: judgeModel,
      summarizerModel: summarizerModel || null,
      totalRounds: finalRounds,
      currentRound: 0,
      completedRounds: [],
      scoringDone: false,
      judgeDone: false,
      startTime: timestamp.toISOString(),
      pausedAt: null,
      // 🎭 اطلاعات نقش‌ها
      roleAssignments: roleAssignments,
      useSmartRoles: useSmartRoles,
      contentAnalysis: contentAnalysis,
      workSheetName: workSheet ? workSheet.getName() : null
    };
    
    saveState(state);
    
    // ذخیره state در Work Sheet
    if (workSheet) {
      saveWorkSheetState(workSheet, state);
    }
    
    // اجرای پردازش
    return continueProcess(state);
    
  } catch (error) {
    Logger.log('❌ خطای کلی: ' + error);
    return {
      success: false,
      error: error.message
    };
  }
}

function continueProcess(state) {
  const totalStart = new Date().getTime();
  
  try {
    // 🔥 پیدا کردن Work Sheet
    let workSheet = null;
    if (state.workSheetName) {
      try {
        const ss = SpreadsheetApp.openById(CONFIG.sheetId);
        workSheet = ss.getSheetByName(state.workSheetName);
        Logger.log('📋 Work Sheet پیدا شد: ' + state.workSheetName);
      } catch (e) {
        Logger.log('⚠️ Work Sheet پیدا نشد');
      }
    } else if (state.promptId) {
      workSheet = findWorkSheet(state.promptId);
    }
    
    // محاسبه تعداد کل مراحل برای progress
    const totalSteps = state.totalRounds + 
                       (MODES[state.mode]?.scoring ? 1 : 0) + 
                       (MODES[state.mode]?.judge ? 1 : 0) + 
                       (MODES[state.mode]?.summary ? 1 : 0) + 1; // +1 برای finalize
    let completedSteps = state.completedRounds.length;
    
    // اجرای دورهای باقی‌مانده
    for (let r = state.currentRound + 1; r <= state.totalRounds; r++) {
      const elapsed = (new Date().getTime() - totalStart) / 1000;
      
      // چک اولیه قبل از شروع دور
      if (elapsed > CONFIG.pauseThreshold - CONFIG.safetyMargin) {
        Logger.log(`⏸️ Pause قبل از دور ${r} (${elapsed.toFixed(1)}s گذشته)`);
        
        state.currentRound = r - 1;
        state.status = QUEUE_STATUS.PAUSED;
        state.pausedAt = new Date().toISOString();
        
        saveState(state);
        
        // 🔥 آپدیت Work Sheet
        if (workSheet) {
          const stepKey = 'ROUND_' + r;
          updateWorkSheetStep(workSheet, stepKey, STEP_STATUS.PAUSED, 'timeout - ادامه خودکار در 1 دقیقه');
          workSheet.getRange('H1').setValue('⏸️ متوقف - ادامه خودکار');
          saveWorkSheetState(workSheet, state);
          SpreadsheetApp.flush();
        }
        
        // 🔥 زمان‌بندی ادامه خودکار
        scheduleAutoResume(state.promptId);
        
        return {
          success: true,
          paused: true,
          autoResume: true,
          promptId: state.promptId,
          message: 'پردازش متوقف شد - ادامه خودکار در 1 دقیقه',
          progress: Math.round((completedSteps / totalSteps) * 100),
          currentRound: state.currentRound,
          totalRounds: state.totalRounds
        };
      }
      
      // 🔥 استفاده از executeRoundWithWorkSheet با globalStartTime
      const roundResult = executeRoundWithWorkSheet(
        state.prompt,
        state.attachments,
        state.models,
        r,
        state.completedRounds,
        state,
        workSheet,
        totalStart  // 🔥 پاس دادن globalStartTime
      );
      
      // 🔥 چک needsPause - اگه وسط دور timeout شد
      if (roundResult.needsPause) {
        Logger.log(`⏸️ Pause در وسط دور ${r} (${roundResult.completedModels} مدل تکمیل شده)`);
        
        // ذخیره پاسخ‌های جزئی
        if (Object.keys(roundResult.responses).length > 0) {
          state.completedRounds.push(roundResult);
          state.partialRound = {
            round: r,
            completedModels: roundResult.completedModels,
            reason: roundResult.pauseReason
          };
        }
        
        state.currentRound = r - 1;  // دور قبلی تکمیل شده
        state.status = QUEUE_STATUS.PAUSED;
        state.pausedAt = new Date().toISOString();
        
        saveState(state);
        
        // 🔥 آپدیت Work Sheet
        if (workSheet) {
          workSheet.getRange('H1').setValue('⏸️ متوقف - ادامه خودکار');
          saveWorkSheetState(workSheet, state);
          SpreadsheetApp.flush();
        }
        
        // 🔥 زمان‌بندی ادامه خودکار
        scheduleAutoResume(state.promptId);
        
        return {
          success: true,
          paused: true,
          autoResume: true,
          promptId: state.promptId,
          message: `پردازش متوقف شد در دور ${r} - ادامه خودکار در 1 دقیقه`,
          progress: Math.round((completedSteps / totalSteps) * 100),
          currentRound: state.currentRound,
          totalRounds: state.totalRounds,
          partialRound: roundResult.completedModels
        };
      }
      
      state.completedRounds.push(roundResult);
      state.currentRound = r;
      completedSteps++;
      
      saveState(state);
      
      // 🔥 آپدیت Work Sheet state
      if (workSheet) {
        saveWorkSheetState(workSheet, state);
        SpreadsheetApp.flush();
      }
    }
    
    // نتیجه‌گیری
    const conclusion = generateConclusion(state.prompt, state.completedRounds, null, null);
    
    // امتیازدهی
    let scoringResult = null;
    const elapsedBeforeScoring = (new Date().getTime() - totalStart) / 1000;
    
    if (MODES[state.mode].scoring && state.models.length > 1 && elapsedBeforeScoring < CONFIG.pauseThreshold) {
      try {
        // 🔥 آپدیت Work Sheet
        if (workSheet) {
          updateWorkSheetStep(workSheet, 'SCORING', STEP_STATUS.RUNNING);
          SpreadsheetApp.flush();
        }
        
        scoringResult = executeScoring(state.promptId, state.prompt, state.models, state.completedRounds);
        state.scoringDone = true;
        completedSteps++;
        
        // 🔥 آپدیت Work Sheet
        if (workSheet) {
          updateWorkSheetStep(workSheet, 'SCORING', STEP_STATUS.DONE, 'تکمیل شد');
          
          // ذخیره امتیازات در Work Sheet
          const scoreRow = 56;
          workSheet.getRange(`A${scoreRow}:H${scoreRow}`).setValues([[
            '📊 امتیازات:', '', '', '', '', '', '', ''
          ]]);
          workSheet.getRange(`A${scoreRow}:H${scoreRow}`).merge().setBackground('#fff3e0');
          
          if (scoringResult && scoringResult.averageScores) {
            let row = scoreRow + 1;
            Object.entries(scoringResult.averageScores).forEach(([model, score]) => {
              workSheet.getRange(`A${row}:D${row}`).setValues([[
                '', model, score + '/100', ''
              ]]);
              row++;
            });
          }
          SpreadsheetApp.flush();
        }
      } catch (error) {
        Logger.log('⚠️ خطا در امتیازدهی: ' + error.message);
        if (workSheet) {
          updateWorkSheetStep(workSheet, 'SCORING', STEP_STATUS.ERROR, null, error.message);
          SpreadsheetApp.flush();
        }
      }
    } else if (workSheet) {
      updateWorkSheetStep(workSheet, 'SCORING', STEP_STATUS.SKIPPED);
      SpreadsheetApp.flush();
    }
    
    // داوری
    let judgeResult = null;
    let judgeScores = null;
    
    if (MODES[state.mode].judge && state.judgeModel && state.models.length >= 2) {
      try {
        // 🔥 آپدیت Work Sheet
        if (workSheet) {
          updateWorkSheetStep(workSheet, 'JUDGING', STEP_STATUS.RUNNING);
          SpreadsheetApp.flush();
        }
        
        judgeResult = executeJudging(
          state.promptId,
          state.prompt,
          state.models,
          state.judgeModel,
          state.completedRounds,
          scoringResult
        );
        
        if (judgeResult && !judgeResult.winner.includes('خطا')) {
          judgeScores = scoreJudgeDetailed(state.promptId, state.models, state.judgeModel, judgeResult, state.prompt);
        }
        
        state.judgeDone = true;
        completedSteps++;
        
        // 🔥 آپدیت Work Sheet
        if (workSheet) {
          updateWorkSheetStep(workSheet, 'JUDGING', STEP_STATUS.DONE, 
            judgeResult?.winner || 'تکمیل شد');
          
          // ذخیره داوری در Work Sheet
          const judgeRow = 62;
          workSheet.getRange(`A${judgeRow}:H${judgeRow}`).setValues([[
            '⚖️ داوری:', state.judgeModel, '', '', '', '', '', ''
          ]]);
          workSheet.getRange(`A${judgeRow}:H${judgeRow}`).merge().setBackground('#e3f2fd');
          
          if (judgeResult) {
            workSheet.getRange(`A${judgeRow + 1}:H${judgeRow + 1}`).setValues([[
              '🏆 برنده:', judgeResult.winner || '', '', '', '', '', '', ''
            ]]);
            workSheet.getRange(`A${judgeRow + 2}:H${judgeRow + 4}`).merge();
            workSheet.getRange(`A${judgeRow + 2}`).setValue(
              judgeResult.reasoning?.substring(0, 500) || ''
            );
          }
          SpreadsheetApp.flush();
        }
      } catch (error) {
        Logger.log('⚠️ خطا در داوری: ' + error.message);
        if (workSheet) {
          updateWorkSheetStep(workSheet, 'JUDGING', STEP_STATUS.ERROR, null, error.message);
          SpreadsheetApp.flush();
        }
      }
    } else if (workSheet) {
      updateWorkSheetStep(workSheet, 'JUDGING', STEP_STATUS.SKIPPED);
      SpreadsheetApp.flush();
    }
    
    // خلاصه‌نویس
    let summaryResult = null;
    const elapsedBeforeSummary = (new Date().getTime() - totalStart) / 1000;
    
    if (MODES[state.mode].summary && state.summarizerModel && elapsedBeforeSummary < CONFIG.pauseThreshold) {
      try {
        Logger.log('📝 شروع خلاصه‌نویسی توسط: ' + state.summarizerModel);
        
        // 🔥 آپدیت Work Sheet
        if (workSheet) {
          updateWorkSheetStep(workSheet, 'SUMMARY', STEP_STATUS.RUNNING);
          SpreadsheetApp.flush();
        }
        
        // ✅ v17.2: ساخت محتوای کامل‌تر برای خلاصه
        let allContent = '';
        state.completedRounds.forEach(round => {
          Object.entries(round.responses).forEach(([model, response]) => {
            const role = round.roles?.[model] || model;
            // ✅ v17.2: افزایش از 500 به 2000 کاراکتر
            allContent += `\n${role}: ${response.substring(0, 2000)}${response.length > 2000 ? '...' : ''}\n`;
          });
        });
        
        summaryResult = generateSummarySimple(
          state.promptId,
          state.prompt,
          state.summarizerModel,
          allContent
        );
        Logger.log('✅ خلاصه تولید شد');
        completedSteps++;
        
        // 🔥 آپدیت Work Sheet
        if (workSheet) {
          updateWorkSheetStep(workSheet, 'SUMMARY', STEP_STATUS.DONE, 'تکمیل شد');
          
          // ذخیره خلاصه در Work Sheet
          const summaryRow = 68;
          workSheet.getRange(`A${summaryRow}:H${summaryRow}`).setValues([[
            '📝 خلاصه:', state.summarizerModel, '', '', '', '', '', ''
          ]]);
          workSheet.getRange(`A${summaryRow}:H${summaryRow}`).merge().setBackground('#f3e5f5');
          
          if (summaryResult && summaryResult.summary) {
            workSheet.getRange(`A${summaryRow + 1}:H${summaryRow + 5}`).merge();
            workSheet.getRange(`A${summaryRow + 1}`).setValue(
              summaryResult.summary.substring(0, 1000)
            );
          }
          SpreadsheetApp.flush();
        }
      } catch (error) {
        Logger.log('⚠️ خطا در خلاصه‌نویسی: ' + error.message);
        if (workSheet) {
          updateWorkSheetStep(workSheet, 'SUMMARY', STEP_STATUS.ERROR, null, error.message);
          SpreadsheetApp.flush();
        }
      }
    } else if (workSheet) {
      updateWorkSheetStep(workSheet, 'SUMMARY', STEP_STATUS.SKIPPED);
      SpreadsheetApp.flush();
    }
    
    // 🔥 نهایی‌سازی
    if (workSheet) {
      updateWorkSheetStep(workSheet, 'FINALIZE', STEP_STATUS.RUNNING);
      SpreadsheetApp.flush();
    }
    
    // ذخیره همه چیز (اختیاری - اگر Sheet/Doc در دسترس نبود، ادامه بده)
    try {
      // 🔥 ذخیره پرامپت
      try {
        saveToSheet_Prompts(
          state.promptId,
          state.startTime,
          state.prompt,
          state.attachments,
          state.mode,
          state.totalRounds,
          state.models,
          state.judgeModel
        );
        Logger.log('✅ پرامپت ذخیره شد');
      } catch (e) {
        Logger.log('⚠️ خطا در ذخیره پرامپت: ' + e);
      }
      
      // 🔥 ذخیره دورها - پاسخ‌های کامل
      try {
        saveToSheet_Rounds(state.promptId, state.completedRounds);
        Logger.log('✅ دورها ذخیره شدند');
      } catch (e) {
        Logger.log('⚠️ خطا در ذخیره دورها: ' + e);
      }
      
      // 🔥 ذخیره تفکر
      try {
        saveToSheet_Thinking(state.promptId, state.completedRounds);
        Logger.log('✅ تفکر ذخیره شد');
      } catch (e) {
        Logger.log('⚠️ خطا در ذخیره تفکر: ' + e);
      }
      
      // 🔥 ذخیره توکن‌ها
      try {
        saveToSheet_Tokens(state.promptId, state.completedRounds);
        Logger.log('✅ توکن‌ها ذخیره شدند');
      } catch (e) {
        Logger.log('⚠️ خطا در ذخیره توکن‌ها: ' + e);
      }
      
      // 🔥 ذخیره امتیازات
      if (scoringResult) {
        try {
          saveToSheet_Scores(state.promptId, scoringResult);
          Logger.log('✅ امتیازات ذخیره شدند');
        } catch (e) {
          Logger.log('⚠️ خطا در ذخیره امتیازات: ' + e);
        }
      }
      
      // 🔥 ذخیره داوری
      if (judgeResult) {
        try {
          saveToSheet_Judge(state.promptId, judgeResult, judgeScores);
          Logger.log('✅ داوری ذخیره شد');
        } catch (e) {
          Logger.log('⚠️ خطا در ذخیره داوری: ' + e);
        }
      }
      
      // 🔥🔥🔥 ذخیره پاسخ‌های کامل در Sheet جداگانه
      try {
        saveFullResponsesToWorkSheet(state.promptId, state.completedRounds);
        Logger.log('✅ پاسخ‌های کامل ذخیره شدند');
      } catch (e) {
        Logger.log('⚠️ خطا در ذخیره پاسخ‌های کامل: ' + e);
      }
      
    } catch (sheetError) {
      Logger.log('⚠️ خطا در ذخیره Sheet (ادامه می‌دهیم): ' + sheetError);
    }
    
    const finalConclusion = generateConclusion(
      state.prompt,
      state.completedRounds,
      scoringResult,
      judgeResult
    );
    
    Logger.log('📄 نتایج در Sheet ذخیره شدند');
    
    // تکمیل شد
    state.status = QUEUE_STATUS.COMPLETED;
    saveState(state);
    
    const totalTime = (new Date().getTime() - totalStart) / 1000;
    
    // 🔥 نهایی کردن Work Sheet
    if (workSheet) {
      updateWorkSheetStep(workSheet, 'FINALIZE', STEP_STATUS.DONE, 
        `کامل شد در ${totalTime.toFixed(1)}s`);
      
      // تغییر نام و رنگ
      finalizeWorkSheet(workSheet, 'COMPLETED');
      
      state.status = QUEUE_STATUS.COMPLETED;
      saveWorkSheetState(workSheet, state);
      SpreadsheetApp.flush();
    }
    
    Logger.log('\n🎉 پردازش کامل شد');
    Logger.log('⏱️ زمان کل: ' + totalTime.toFixed(1) + ' ثانیه');
    
    // حذف از صف
    try {
      deleteState(state.promptId);
    } catch (e) {
      Logger.log('⚠️ خطا در حذف State: ' + e);
    }
    
    // 🔥 ساخت result قبل از return
    const finalResult = {
      success: true,
      paused: false,
      promptId: state.promptId,
      prompt: state.prompt,  // 🔥 اضافه کردن prompt
      mode: state.mode,
      rounds: state.completedRounds.length,
      results: state.completedRounds,
      conclusion: finalConclusion,
      scoring: scoringResult,
      judge: judgeResult,
      summary: summaryResult,
      processingTime: totalTime,
      // 🎭 اطلاعات نقش‌ها
      roles: state.roleAssignments ? state.roleAssignments.map(r => ({
        role: r.roleName,
        icon: r.icon,
        model: r.modelId
      })) : null
    };
    
    Logger.log('✅ آماده برگشت نتیجه به Frontend');
    
    return finalResult;
    
  } catch (error) {
    Logger.log('❌ خطا در پردازش: ' + error);
    
    state.status = QUEUE_STATUS.ERROR;
    saveState(state);
    
    // 🔥 آپدیت Work Sheet با خطا
    if (state.workSheetName) {
      try {
        const workSheet = findWorkSheet(state.promptId);
        if (workSheet) {
          workSheet.getRange('H1').setValue('❌ خطا');
          workSheet.setTabColor('#f44336');
          SpreadsheetApp.flush();
        }
      } catch (e) {}
    }
    
    return {
      success: false,
      error: error.message,
      promptId: state.promptId
    };
  }
}

// ========================================
// 🔄 AUTO-RESUME SYSTEM - ادامه خودکار
// ========================================

/**
 * زمان‌بندی ادامه خودکار با Trigger واقعی
 */
function scheduleAutoResume(promptId) {
  Logger.log('\n🔄 === SCHEDULE AUTO-RESUME ===');
  Logger.log('📌 promptId: ' + promptId);
  
  try {
    // حذف trigger های قبلی
    Logger.log('🗑️ حذف trigger های قبلی...');
    const triggers = ScriptApp.getProjectTriggers();
    let deletedCount = 0;
    triggers.forEach(trigger => {
      if (trigger.getHandlerFunction() === 'autoResumeHandler') {
        ScriptApp.deleteTrigger(trigger);
        deletedCount++;
      }
    });
    Logger.log('  ' + deletedCount + ' trigger حذف شد');
    
    // ذخیره promptId در Properties
    Logger.log('💾 ذخیره در Properties...');
    PropertiesService.getScriptProperties().setProperty('PENDING_AUTO_RESUME', promptId);
    PropertiesService.getScriptProperties().setProperty('PENDING_AUTO_RESUME_TIME', new Date().getTime().toString());
    
    // 🔥 ایجاد Trigger واقعی - 1 دقیقه بعد
    Logger.log('⏰ ایجاد Trigger جدید...');
    const newTrigger = ScriptApp.newTrigger('autoResumeHandler')
      .timeBased()
      .after(60 * 1000)  // 60 ثانیه
      .create();
    
    Logger.log('✅ Trigger ایجاد شد!');
    Logger.log('  ID: ' + newTrigger.getUniqueId());
    Logger.log('  Handler: ' + newTrigger.getHandlerFunction());
    Logger.log('🔄 ادامه خودکار در 60 ثانیه...');
    
    return true;
    
  } catch (error) {
    Logger.log('❌ خطا در ایجاد trigger: ' + error);
    Logger.log('  Stack: ' + error.stack);
    
    // 🔥 Fallback: ذخیره state برای ادامه دستی
    try {
      PropertiesService.getScriptProperties().setProperty('FAILED_AUTO_RESUME', promptId);
      Logger.log('💾 promptId برای ادامه دستی ذخیره شد');
    } catch (e) {}
    
    return false;
  }
}

/**
 * Handler که توسط Trigger اجرا می‌شود
 */
function autoResumeHandler() {
  try {
    Logger.log('\n' + '='.repeat(60));
    Logger.log('🔄 AUTO-RESUME HANDLER اجرا شد');
    Logger.log('='.repeat(60));
    
    const promptId = PropertiesService.getScriptProperties().getProperty('PENDING_AUTO_RESUME');
    
    if (!promptId) {
      Logger.log('⚠️ promptId پیدا نشد');
      return;
    }
    
    Logger.log('📌 ادامه پردازش: ' + promptId);
    
    // پاک کردن
    PropertiesService.getScriptProperties().deleteProperty('PENDING_AUTO_RESUME');
    PropertiesService.getScriptProperties().deleteProperty('PENDING_AUTO_RESUME_TIME');
    
    // ادامه پردازش
    const result = resumeProcess(promptId);
    
    Logger.log('✅ نتیجه: ' + JSON.stringify(result).substring(0, 300));
    
  } catch (error) {
    Logger.log('❌ خطا در autoResumeHandler: ' + error);
  }
}

/**
 * 🧪 تست ایجاد Trigger - برای اطمینان از کارکرد
 */
function testTriggerCreation() {
  Logger.log('\n🧪 === تست ایجاد Trigger ===');
  
  try {
    // لیست trigger های موجود
    const existingTriggers = ScriptApp.getProjectTriggers();
    Logger.log('📋 تعداد trigger های موجود: ' + existingTriggers.length);
    existingTriggers.forEach((t, i) => {
      Logger.log('  ' + (i+1) + '. ' + t.getHandlerFunction() + ' - ' + t.getUniqueId());
    });
    
    // ایجاد trigger تست
    Logger.log('\n⏰ ایجاد trigger تست...');
    const testTrigger = ScriptApp.newTrigger('testTriggerHandler')
      .timeBased()
      .after(30 * 1000)  // 30 ثانیه
      .create();
    
    Logger.log('✅ Trigger تست ایجاد شد!');
    Logger.log('  ID: ' + testTrigger.getUniqueId());
    
    // لیست بعد از ایجاد
    const newTriggers = ScriptApp.getProjectTriggers();
    Logger.log('\n📋 تعداد trigger ها بعد از ایجاد: ' + newTriggers.length);
    
    return {
      success: true,
      triggerId: testTrigger.getUniqueId(),
      totalTriggers: newTriggers.length
    };
    
  } catch (error) {
    Logger.log('❌ خطا: ' + error);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Handler تست
 */
function testTriggerHandler() {
  Logger.log('🧪 TEST TRIGGER HANDLER اجرا شد!');
  Logger.log('زمان: ' + new Date().toISOString());
}

/**
 * بررسی آیا پردازش در انتظار ادامه است
 */
function checkPendingResume() {
  try {
    const promptId = PropertiesService.getScriptProperties().getProperty('PENDING_AUTO_RESUME');
    const savedTime = PropertiesService.getScriptProperties().getProperty('PENDING_AUTO_RESUME_TIME');
    
    if (!promptId) {
      return { pending: false };
    }
    
    const elapsed = savedTime ? (new Date().getTime() - parseInt(savedTime)) / 1000 : 0;
    
    return {
      pending: true,
      promptId: promptId,
      elapsedSeconds: Math.round(elapsed),
      canResume: elapsed > 30 // بعد از 30 ثانیه می‌تونه ادامه بده
    };
    
  } catch (error) {
    return { pending: false, error: error.message };
  }
}

/**
 * دریافت آخرین پردازش در حال انجام
 */
function getLastProcessing() {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    const sheets = ss.getSheets();
    
    let latestSheet = null;
    let latestTime = 0;
    let latestPromptId = null;
    
    // پیدا کردن آخرین Work Sheet
    for (const sheet of sheets) {
      const name = sheet.getName();
      if (name.startsWith('WORK-') && !name.includes('[آرشیو]')) {
        // استخراج promptId از نام
        const match = name.match(/WORK-([A-Za-z0-9_]+)/);
        if (match) {
          const shortId = match[1];
          
          // چک کردن زمان ایجاد از محتوای شیت
          try {
            const timestampCell = sheet.getRange('B2').getValue();
            const timestamp = timestampCell ? new Date(timestampCell).getTime() : 0;
            
            if (timestamp > latestTime) {
              latestTime = timestamp;
              latestSheet = sheet;
              
              // خواندن promptId کامل از J1
              const stateStr = sheet.getRange('J1').getValue();
              if (stateStr) {
                try {
                  const state = JSON.parse(stateStr);
                  latestPromptId = state.promptId;
                } catch (e) {
                  // ساخت promptId از نام شیت
                  latestPromptId = 'AI_' + shortId;
                }
              } else {
                latestPromptId = 'AI_' + shortId;
              }
            }
          } catch (e) {
            // ignore
          }
        }
      }
    }
    
    if (latestPromptId) {
      // چک کردن وضعیت
      const status = latestSheet ? latestSheet.getRange('H1').getValue() : '';
      const isCompleted = status && (status.includes('کامل') || status.includes('COMPLETED'));
      
      return {
        success: true,
        promptId: latestPromptId,
        sheetName: latestSheet ? latestSheet.getName() : null,
        status: status,
        isCompleted: isCompleted
      };
    }
    
    return { success: false, error: 'پردازشی یافت نشد' };
    
  } catch (error) {
    Logger.log('❌ خطا در getLastProcessing: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * ادامه خودکار پردازش معلق
 */
function autoResumePending() {
  try {
    const pending = checkPendingResume();
    
    if (!pending.pending || !pending.promptId) {
      return { success: false, error: 'پردازش معلقی وجود ندارد' };
    }
    
    Logger.log('🔄 ادامه خودکار پردازش: ' + pending.promptId);
    
    // پاک کردن
    PropertiesService.getScriptProperties().deleteProperty('PENDING_AUTO_RESUME');
    PropertiesService.getScriptProperties().deleteProperty('PENDING_AUTO_RESUME_TIME');
    
    // ادامه
    return resumeProcess(pending.promptId);
    
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * خواندن وضعیت مدل‌ها از Work Sheet
 */
function getModelStatusesFromWorkSheet(workSheet) {
  try {
    const statuses = [];
    
    for (let i = 1; i <= 8; i++) {
      const row = 5 + i;
      const model = workSheet.getRange(`B${row}`).getValue();
      const role = workSheet.getRange(`C${row}`).getValue();
      const status = workSheet.getRange(`E${row}`).getValue();
      
      if (model && model !== '') {
        let statusText = 'در انتظار';
        if (status && status.includes('تکمیل')) {
          statusText = 'تکمیل';
        } else if (status && status.includes('اجرا')) {
          statusText = 'در حال اجرا';
        } else if (status && status.includes('خطا')) {
          statusText = 'خطا';
        }
        
        statuses.push({
          name: model,
          role: role || '',
          status: statusText
        });
      }
    }
    
    return statuses;
  } catch (e) {
    Logger.log('⚠️ خطا در خواندن وضعیت مدل‌ها: ' + e);
    return null;
  }
}

/**
 * دریافت نتایج کامل یک پردازش
 */
function getResults(promptId) {
  try {
    Logger.log('📥 getResults: ' + promptId);
    
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    
    // 🔥 اول از Work Sheet بخوان (منبع اصلی)
    const workSheet = findWorkSheet(promptId);
    if (workSheet) {
      const result = buildResultsFromWorkSheet(workSheet, promptId);
      if (result && result.results && result.results.length > 0) {
        Logger.log('✅ نتایج از Work Sheet: ' + result.results.length + ' دور');
        return result;
      }
    }
    
    // 🔥 سپس از Done Sheet بخوان
    const doneSheet = findDoneSheet(promptId);
    if (doneSheet) {
      const result = buildResultsFromWorkSheet(doneSheet, promptId);
      if (result && result.results && result.results.length > 0) {
        Logger.log('✅ نتایج از Done Sheet: ' + result.results.length + ' دور');
        return result;
      }
    }
    
    // جستجو در آرشیو
    const archiveSheet = ss.getSheetByName('آرشیو');
    if (archiveSheet) {
      const data = archiveSheet.getDataRange().getValues();
      for (let i = 1; i < data.length; i++) {
        if (data[i][0] === promptId) {
          return {
            success: true,
            promptId: promptId,
            prompt: data[i][2] || '',
            mode: data[i][4] || '',
            results: [],
            conclusion: data[i][8] || ''
          };
        }
      }
    }
    
    return { success: false, error: 'نتایج یافت نشد' };
    
  } catch (error) {
    Logger.log('❌ خطا در getResults: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * 🔥 ساخت نتایج از Work Sheet
 */
function buildResultsFromWorkSheet(sheet, promptId) {
  try {
    const sheetName = sheet.getName();
    
    // خواندن اطلاعات اصلی
    const stateJson = sheet.getRange('J1').getValue();
    let state = {};
    if (stateJson) {
      try { state = JSON.parse(stateJson); } catch(e) {}
    }
    
    const prompt = sheet.getRange('D2').getValue() || state.prompt || '';
    const mode = sheet.getRange('C1').getValue() || state.mode || '';
    
    // خواندن پاسخ‌ها از جدول پاسخ‌ها (ردیف 34+)
    const roundsData = {};
    
    for (let i = 0; i < 50; i++) {
      const row = 34 + i;
      const roundNum = sheet.getRange(`A${row}`).getValue();
      const model = sheet.getRange(`B${row}`).getValue();
      const role = sheet.getRange(`C${row}`).getValue();
      const responsePreview = sheet.getRange(`D${row}`).getValue();
      const responseLength = sheet.getRange(`E${row}`).getValue();
      const tokens = sheet.getRange(`F${row}`).getValue();
      const time = sheet.getRange(`G${row}`).getValue();
      const status = sheet.getRange(`H${row}`).getValue();
      
      if (!model || model === '') break;
      
      if (status && status.includes('تکمیل')) {
        if (!roundsData[roundNum]) {
          roundsData[roundNum] = { responses: {}, processingTime: 0 };
        }
        
        // خواندن پاسخ کامل از Cache
        const fullResponse = readFullResponseFromCache(sheetName, roundNum, model);
        roundsData[roundNum].responses[model] = fullResponse || responsePreview;
        
        // زمان پردازش
        if (time) {
          const timeNum = parseFloat(time.toString().replace('s', ''));
          roundsData[roundNum].processingTime += timeNum || 0;
        }
      }
    }
    
    // تبدیل به آرایه
    const results = [];
    const sortedRounds = Object.keys(roundsData).sort((a, b) => parseInt(a) - parseInt(b));
    for (const roundNum of sortedRounds) {
      results.push({
        round: parseInt(roundNum),
        responses: roundsData[roundNum].responses,
        processingTime: roundsData[roundNum].processingTime
      });
    }
    
    // خواندن نتایج داوری و خلاصه
    let conclusion = '';
    let judge = null;
    
    // از state
    if (state.summaryResult) {
      conclusion = state.summaryResult;
    }
    if (state.judgeResult) {
      judge = state.judgeResult;
    }
    
    return {
      success: true,
      promptId: promptId,
      prompt: prompt,
      mode: mode,
      results: results,
      conclusion: conclusion,
      judge: judge
    };
    
  } catch (e) {
    Logger.log('⚠️ خطا در buildResultsFromWorkSheet: ' + e);
    return null;
  }
}

/**
 * پیدا کردن Done Sheet
 */
function findDoneSheet(promptId) {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    const sheetName = '✅ Done_' + promptId.substring(3, 18);
    return ss.getSheetByName(sheetName);
  } catch (e) {
    return null;
  }
}

/**
 * دریافت وضعیت پردازش (برای polling از frontend)
 */
function getProcessStatus(promptId) {
  try {
    // چک کردن پردازش معلق
    const pending = checkPendingResume();
    
    // اگر promptId داده نشده، از pending استفاده کن
    if (!promptId && pending.pending) {
      promptId = pending.promptId;
    }
    
    if (!promptId) {
      return { success: false, error: 'promptId مشخص نشده' };
    }
    
    Logger.log('📊 getProcessStatus: ' + promptId);
    
    // 🔥 چک کردن lock - اگه lock فعاله، یعنی در حال اجراست
    const lockKey = 'RESUME_LOCK_' + promptId;
    const existingLock = PropertiesService.getScriptProperties().getProperty(lockKey);
    let isLocked = false;
    let lockElapsed = 0;
    
    if (existingLock) {
      const lockTime = parseInt(existingLock);
      const now = new Date().getTime();
      lockElapsed = (now - lockTime) / 1000;
      
      if (lockElapsed < 300) {  // کمتر از 5 دقیقه
        isLocked = true;
        Logger.log('🔒 Lock فعال است (' + lockElapsed.toFixed(0) + 's)');
      }
    }
    
    // اول از Work Sheet بخوان
    const workSheet = findWorkSheet(promptId);
    let state = null;
    let fromWorkSheet = false;
    
    if (workSheet) {
      state = loadWorkSheetState(workSheet);
      fromWorkSheet = !!state;
      
      // 🔥 اگر state از Work Sheet نخواند، اطلاعات پایه رو مستقیم بخوان
      if (!state) {
        Logger.log('⚠️ State از J1 خوانده نشد، خواندن مستقیم...');
        
        const statusCell = workSheet.getRange('H1').getValue();
        const totalRounds = parseInt(workSheet.getRange('D2').getValue()) || 1;
        
        // شمارش مدل‌های تکمیل شده و کل مدل‌ها
        let completedModels = 0;
        let totalModelsInSheet = 0;
        for (let i = 1; i <= 8; i++) {
          const model = workSheet.getRange(`B${5+i}`).getValue();
          const status = workSheet.getRange(`E${5+i}`).getValue();
          
          if (model && model !== '') {
            totalModelsInSheet++;
            if (status && status.includes('تکمیل')) {
              completedModels++;
            }
          }
        }
        
        // 🔥 محاسبه بهتر progress
        // فرمول: (مدل‌های تکمیل شده / کل مراحل) * 100
        // کل مراحل = مدل‌ها + scoring + judge + summary + finalize
        const totalSteps = totalModelsInSheet + 4; // 4 مرحله اضافی
        const currentProgress = Math.round((completedModels / totalSteps) * 100);
        
        // 🔥 تعیین status - اگه lock فعاله، RUNNING
        let status = isLocked ? 'RUNNING' : 'PAUSED';
        if (statusCell && statusCell.includes('کامل')) {
          status = 'COMPLETED';
        } else if (statusCell && statusCell.includes('اجرا')) {
          status = 'RUNNING';
        }
        
        // 🔥 پیدا کردن مدل فعلی
        let currentModelName = 'در انتظار';
        for (let i = 1; i <= 8; i++) {
          const model = workSheet.getRange(`B${5+i}`).getValue();
          const modelStatus = workSheet.getRange(`E${5+i}`).getValue();
          if (model && (!modelStatus || !modelStatus.includes('تکمیل'))) {
            currentModelName = model;
            break;
          }
        }
        
        return {
          success: true,
          promptId: promptId,
          status: status,
          progress: currentProgress,
          currentRound: completedModels >= totalModelsInSheet ? 1 : 0,
          totalRounds: totalRounds,
          completedRounds: completedModels >= totalModelsInSheet ? 1 : 0,
          completedModels: completedModels,
          totalModels: totalModelsInSheet,
          currentModel: isLocked ? 'در حال پردازش...' : currentModelName,
          isPending: true,
          canResume: !isLocked,
          isLocked: isLocked,
          lockElapsed: lockElapsed,
          source: 'worksheet-direct',
          // 🔥 اضافه کردن وضعیت هر مدل
          modelStatuses: getModelStatusesFromWorkSheet(workSheet)
        };
      }
    }
    
    if (state) {
      // محاسبه progress
      const totalSteps = (state.totalRounds || 1) + 
                        (MODES[state.mode]?.scoring ? 1 : 0) + 
                        (MODES[state.mode]?.judge ? 1 : 0) + 
                        (MODES[state.mode]?.summary ? 1 : 0) + 1;
      const completedSteps = state.completedRounds?.length || 0;
      
      // 🔥 دریافت زمان آخرین resume
      const lastResumeTime = PropertiesService.getScriptProperties().getProperty('LAST_RESUME_TIME_' + promptId);
      
      // 🔥 تعیین status - اگه lock فعاله، RUNNING
      const effectiveStatus = isLocked ? 'RUNNING' : (state.status || 'PAUSED');
      
      // 🔥 محاسبه تعداد مدل‌های تکمیل شده از Work Sheet
      const models = state.models || [];
      let completedModels = 0;
      let currentModel = 'در انتظار';
      
      if (workSheet) {
        // خواندن از Work Sheet
        for (let i = 1; i <= 8; i++) {
          const model = workSheet.getRange(`B${5+i}`).getValue();
          const modelStatus = workSheet.getRange(`E${5+i}`).getValue();
          if (model && model !== '') {
            if (modelStatus && modelStatus.includes('تکمیل')) {
              completedModels++;
            } else if (currentModel === 'در انتظار') {
              currentModel = model;  // اولین مدل تکمیل نشده
            }
          }
        }
      } else {
        // fallback به state
        completedModels = state.completedRounds?.length > 0 ? models.length : 0;
      }
      
      // 🔥 محاسبه بهتر progress
      const totalModelsCount = models.length || 3;
      const totalStepsReal = totalModelsCount + 
                            (MODES[state.mode]?.scoring ? 1 : 0) + 
                            (MODES[state.mode]?.judge ? 1 : 0) + 
                            (MODES[state.mode]?.summary ? 1 : 0) + 1;
      const progressReal = Math.round((completedModels / totalStepsReal) * 100);
      
      return {
        success: true,
        promptId: promptId,
        status: effectiveStatus,
        progress: progressReal,
        currentRound: state.currentRound || 0,
        totalRounds: state.totalRounds || 1,
        completedRounds: completedSteps,
        completedModels: completedModels,
        totalModels: totalModelsCount,
        currentModel: isLocked ? 'در حال پردازش...' : currentModel,
        models: models,
        isPending: pending.pending && pending.promptId === promptId,
        canResume: !isLocked,
        isLocked: isLocked,
        lockElapsed: lockElapsed,
        lastResumeTime: lastResumeTime ? parseInt(lastResumeTime) : null,
        source: fromWorkSheet ? 'worksheet' : 'cache',
        roles: state.roleAssignments?.map(r => ({
          role: r.roleName,
          icon: r.icon,
          model: r.modelId
        })),
        // 🔥 وضعیت هر مدل
        modelStatuses: workSheet ? getModelStatusesFromWorkSheet(workSheet) : null
      };
    }
    
    // از Cache/Sheet بخوان
    const cachedState = loadState(promptId);
    if (cachedState) {
      const totalSteps = (cachedState.totalRounds || 1) + 
                        (MODES[cachedState.mode]?.scoring ? 1 : 0) + 
                        (MODES[cachedState.mode]?.judge ? 1 : 0) + 
                        (MODES[cachedState.mode]?.summary ? 1 : 0) + 1;
      const completedSteps = cachedState.completedRounds?.length || 0;
      
      // 🔥 دریافت زمان آخرین resume
      const lastResumeTime = PropertiesService.getScriptProperties().getProperty('LAST_RESUME_TIME_' + promptId);
      
      return {
        success: true,
        promptId: promptId,
        status: cachedState.status || 'PAUSED',
        progress: Math.round((completedSteps / totalSteps) * 100),
        currentRound: cachedState.currentRound || 0,
        totalRounds: cachedState.totalRounds || 1,
        completedRounds: completedSteps,
        isPending: pending.pending && pending.promptId === promptId,
        canResume: true,
        lastResumeTime: lastResumeTime ? parseInt(lastResumeTime) : null,
        source: 'cache'
      };
    }
    
    // 🔥 حتی اگه state پیدا نشد، اطلاعات Work Sheet رو برگردون
    return {
      success: false,
      error: 'State پیدا نشد',
      isPending: pending.pending,
      pendingPromptId: pending.promptId,
      canResume: !!workSheet,  // اگه Work Sheet هست، می‌شه resume کرد
      hasWorkSheet: !!workSheet
    };
    
  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
}

function resumeProcess(promptId) {
  const startTime = new Date().getTime();
  
  try {
    Logger.log('▶️ Resume: ' + promptId);
    
    // 🔥 Journal: شروع resume
    logToJournal(promptId, '▶️ Resume', 'شروع ادامه پردازش', '🔄');
    
    // 1. پیدا کردن Work Sheet
    const workSheet = findWorkSheet(promptId);
    if (!workSheet) {
      logToJournal(promptId, '❌ خطا', 'Work Sheet پیدا نشد', '❌');
      Logger.log('❌ Work Sheet پیدا نشد');
      return { success: false, error: 'Work Sheet not found' };
    }
    
    // 2. خواندن state
    let state = loadWorkSheetState(workSheet);
    if (!state) {
      state = loadState(promptId);
    }
    if (!state) {
      state = rebuildStateFromWorkSheet(workSheet, promptId);
    }
    if (!state) {
      logToJournal(promptId, '❌ خطا', 'State پیدا نشد', '❌');
      return { success: false, error: 'State not found' };
    }
    
    // 🔥 Journal: وضعیت فعلی
    logToJournal(promptId, '📊 وضعیت', 
      'دور: ' + (state.currentRound || 0) + '/' + state.totalRounds + 
      ' - مدل‌های partial: ' + (state.currentRoundResponses ? Object.keys(state.currentRoundResponses).length : 0), 
      '🔄');
    
    // 3. چک کردن اگه قبلاً تکمیل شده
    if (state.status === QUEUE_STATUS.COMPLETED) {
      logToJournal(promptId, '✅ تکمیل', 'قبلاً تکمیل شده بود', '✅');
      Logger.log('✅ قبلاً تکمیل شده');
      return { 
        success: true, 
        paused: false, 
        completed: true,
        progress: 100 
      };
    }
    
    // 4. تنظیم status
    state.status = QUEUE_STATUS.RUNNING;
    
    // 5. پردازش یک مدل
    const result = processOneStep(state, workSheet, startTime);
    
    // 6. ذخیره state
    saveState(state);
    saveWorkSheetState(workSheet, state);
    
    // 7. برگرداندن نتیجه
    const progress = calculateProgress(state);
    Logger.log('📊 Progress: ' + progress + '%');
    
    // 🔥 تعیین status برای Frontend
    let returnStatus = state.status;
    if (result.completed) {
      returnStatus = 'COMPLETED';
    } else if (result.paused) {
      returnStatus = 'PAUSED';
    }
    
    return {
      success: true,
      paused: result.paused,
      completed: result.completed,
      status: returnStatus,  // 🔥 اضافه کردن status
      progress: progress,
      currentRound: state.currentRound,
      totalRounds: state.totalRounds,
      completedModels: Object.keys(state.currentRoundResponses || {}).length,
      totalModels: state.models?.length || 3,
      promptId: promptId
    };
    
  } catch (error) {
    Logger.log('❌ Resume error: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * پردازش یک قدم (یک مدل یا یک مرحله)
 */
function processOneStep(state, workSheet, startTime) {
  const elapsed = () => (new Date().getTime() - startTime) / 1000;
  
  // چک timeout
  if (elapsed() > 200) {
    Logger.log('⏱️ نزدیک timeout - pause');
    state.status = QUEUE_STATUS.PAUSED;
    return { paused: true, completed: false };
  }
  
  // اگه همه دورها تکمیل شده
  if (state.currentRound >= state.totalRounds) {
    // مراحل بعدی (scoring, judge, summary)
    const mode = MODES[state.mode] || {};
    
    // Scoring
    if (mode.scoring && !state.scoringDone) {
      Logger.log('📊 شروع امتیازدهی...');
      try {
        const scoringResult = executeScoring(state.promptId, state.prompt, state.models, state.completedRounds);
        state.scoringResult = scoringResult;
        state.scoringDone = true;
        saveWorkSheetState(workSheet, state);
        updateWorkSheetStep(workSheet, 'SCORING', STEP_STATUS.COMPLETED, 'تکمیل');
      } catch (e) {
        Logger.log('⚠️ خطا در امتیازدهی: ' + e);
        state.scoringDone = true; // رد کن
      }
      if (elapsed() > 180) {
        state.status = QUEUE_STATUS.PAUSED;
        return { paused: true, completed: false };
      }
    }
    
    // Judge
    if (mode.judge && !state.judgeDone) {
      Logger.log('⚖️ شروع داوری...');
      try {
        const judgeModel = state.judgeModel || selectBestJudgeModel(state.models);
        const judgeResult = executeJudging(state.promptId, state.prompt, state.models, judgeModel, state.completedRounds, state.scoringResult);
        state.judgeResult = judgeResult;
        state.judgeDone = true;
        saveWorkSheetState(workSheet, state);
        updateWorkSheetStep(workSheet, 'JUDGE', STEP_STATUS.COMPLETED, 'تکمیل');
      } catch (e) {
        Logger.log('⚠️ خطا در داوری: ' + e);
        state.judgeDone = true; // رد کن
      }
      if (elapsed() > 180) {
        state.status = QUEUE_STATUS.PAUSED;
        return { paused: true, completed: false };
      }
    }
    
    // Summary
    if (mode.summary && !state.summaryDone) {
      Logger.log('📝 شروع خلاصه...');
      try {
        const summaryModel = state.summaryModel || selectBestSummaryModel(state.models);
        const summaryResult = generateSummarySimple(state.promptId, state.prompt, summaryModel, state.completedRounds);
        state.summaryResult = summaryResult;
        state.summaryDone = true;
        saveWorkSheetState(workSheet, state);
        updateWorkSheetStep(workSheet, 'SUMMARY', STEP_STATUS.COMPLETED, 'تکمیل');
      } catch (e) {
        Logger.log('⚠️ خطا در خلاصه: ' + e);
        state.summaryDone = true; // رد کن
      }
    }
    
    // Finalize
    Logger.log('🎉 نهایی‌سازی...');
    try {
      // 🔥 اطمینان از بازسازی completedRounds از Work Sheet
      if (!state.completedRounds || state.completedRounds.length === 0) {
        state.completedRounds = rebuildCompletedRoundsFromWorkSheet(workSheet, state);
        Logger.log('📋 بازسازی completedRounds برای finalize: ' + state.completedRounds.length + ' دور');
      }
      
      // اگه هنوز خالیه، log بزن
      if (!state.completedRounds || state.completedRounds.length === 0) {
        Logger.log('⚠️ completedRounds خالیه! finalize بدون پاسخ‌ها');
        logToJournal(state.promptId, '⚠️ هشدار', 'completedRounds خالیه', '⚠️');
      } else {
        Logger.log('✅ completedRounds آماده: ' + state.completedRounds.length + ' دور');
      }
      
      // 🔥 ذخیره پرامپت در آرشیو
      saveToSheet_Prompts(
        state.promptId,
        state.startTime,
        state.prompt,
        state.attachments,
        state.mode,
        state.totalRounds,
        state.models,
        state.judgeModel
      );
      Logger.log('✅ پرامپت ذخیره شد در آرشیو');
      
      // ذخیره نتایج
      saveToSheet_Scores(state.promptId, state.scoringResult);
      saveToSheet_Judge(state.promptId, state.judgeResult, null);
      
      // ذخیره دورها
      saveToSheet_Rounds(state.promptId, state.completedRounds);
      
      // ذخیره پاسخ‌های کامل
      saveFullResponsesToWorkSheet(state.promptId, state.completedRounds);
      
      // 🔥 Journal: تکمیل
      logToJournal(state.promptId, '🎉 تکمیل', 
        (state.completedRounds?.length || 0) + ' دور، ' + state.models.length + ' مدل', '✅');
        
    } catch (e) {
      Logger.log('⚠️ خطا در نهایی‌سازی: ' + e);
      logToJournal(state.promptId, '❌ خطا', 'نهایی‌سازی: ' + e.message, '❌');
    }
    
    state.status = QUEUE_STATUS.COMPLETED;
    state.completedAt = new Date().toISOString();
    workSheet.getRange('H1').setValue('✅ تکمیل شده');
    finalizeWorkSheet(workSheet, 'تکمیل');
    
    return { paused: false, completed: true };
  }
  
  // پردازش دور بعدی (یا ادامه دور فعلی)
  const nextRound = state.currentRound + 1;
  
  // چک کن آیا در وسط دور هستیم
  const isPartialRound = state.currentRoundResponses && Object.keys(state.currentRoundResponses).length > 0;
  
  if (isPartialRound) {
    Logger.log('🔄 ادامه دور ' + nextRound + ' (partial)');
  } else {
    Logger.log('🔄 شروع دور ' + nextRound);
  }
  
  updateWorkSheetStep(workSheet, 'ROUND_' + nextRound, STEP_STATUS.RUNNING, 'در حال اجرا');
  
  const roundResult = executeRoundSimple(state, workSheet, startTime);
  
  if (roundResult.success) {
    // 🔥 اطمینان از وجود completedRounds
    if (!state.completedRounds) {
      state.completedRounds = [];
    }
    
    // دور کامل شد
    state.completedRounds.push(roundResult.roundData);
    state.currentRound = nextRound;
    updateWorkSheetStep(workSheet, 'ROUND_' + nextRound, STEP_STATUS.COMPLETED, 
      roundResult.completedModels + ' پاسخ (' + roundResult.time.toFixed(1) + 's)');
    Logger.log('✅ دور ' + nextRound + ' کامل شد');
  } else if (roundResult.partial) {
    // دور هنوز کامل نشده - state ذخیره شده
    Logger.log('⏸️ دور ' + nextRound + ' partial - ' + roundResult.completedModels + ' مدل تکمیل');
  }
  
  // Pause
  state.status = QUEUE_STATUS.PAUSED;
  return { paused: true, completed: false };
}

/**
 * اجرای ساده یک دور - فقط یک مدل در هر بار!
 */
function executeRoundSimple(state, workSheet, startTime) {
  const roundStart = new Date().getTime();
  
  // 🔥 خواندن پاسخ‌های قبلی از Work Sheet (نه از state!)
  const existingResponses = readResponsesFromWorkSheet(workSheet, state.currentRound + 1);
  
  const responses = existingResponses.responses || {};
  const tokens = existingResponses.tokens || {};
  const roles = state.currentRoundRoles || {};
  let completedModels = Object.keys(responses).length;
  let processedInThisCall = 0;
  
  Logger.log('📋 مدل‌های قبلاً تکمیل شده در دور ' + (state.currentRound + 1) + ': ' + completedModels + ' از ' + state.models.length);
  Logger.log('📋 مدل‌های تکمیل شده: ' + Object.keys(responses).join(', '));
  
  // 🔥 Journal: وضعیت دور
  logToJournal(state.promptId, '🔄 دور ' + (state.currentRound + 1), 
    completedModels + '/' + state.models.length + ' مدل تکمیل', '🔄');
  
  for (const model of state.models) {
    // 🔥 Skip اگر قبلاً تکمیل شده
    if (responses[model]) {
      Logger.log('⏭️ Skip ' + model + ' (قبلاً تکمیل شده)');
      continue;
    }
    
    const elapsed = (new Date().getTime() - startTime) / 1000;
    if (elapsed > 150) {  // 2.5 دقیقه
      Logger.log('⏱️ Timeout - pause برای resume بعدی');
      
      // 🔥 Journal: timeout
      logToJournal(state.promptId, '⏱️ Timeout', 'pause بعد از ' + elapsed.toFixed(0) + 's', '⏸️');
      
      return {
        success: false,
        partial: true,
        completedModels: completedModels,
        time: (new Date().getTime() - roundStart) / 1000
      };
    }
    
    try {
      Logger.log('🤖 فراخوانی ' + model);
      
      // آپدیت Work Sheet - نشون بده کدوم مدل در حال اجراست
      updateModelInWorkSheet(workSheet, model, '🔄 در حال اجرا...');
      
      // نقش
      const roleAssignment = state.roleAssignments?.find(r => r.modelId === model);
      const role = roleAssignment?.roleName || model;
      roles[model] = role;
      
      // 🔥 Journal: شروع فراخوانی
      logToJournal(state.promptId, '🤖 فراخوانی', model + ' (' + role + ')', '🔄');
      
      // ساخت prompt
      let fullPrompt = state.prompt;
      if (roleAssignment?.systemPrompt) {
        fullPrompt = roleAssignment.systemPrompt + '\n\n' + state.prompt;
      }
      
      // اضافه کردن context از دورهای قبل - ✅ v17.2: با طول کافی
      if (state.completedRounds && state.completedRounds.length > 0) {
        fullPrompt += '\n\n--- پاسخ‌های قبلی ---\n';
        state.completedRounds.forEach((round, idx) => {
          Object.entries(round.responses || {}).forEach(([m, r]) => {
            // ✅ v17.2: افزایش از 300 به 1500 کاراکتر
            fullPrompt += `\n[${m}]: ${r.substring(0, 1500)}${r.length > 1500 ? '...' : ''}\n`;
          });
        });
      }
      
      // فراخوانی API
      const modelStart = new Date().getTime();
      const result = callModel(model, fullPrompt, state.attachments || []);
      const modelTime = (new Date().getTime() - modelStart) / 1000;
      
      if (result && result.response) {
        responses[model] = result.response;
        tokens[model] = result.tokens || 0;
        completedModels++;
        processedInThisCall++;
        
        // 🔥 آپدیت Work Sheet - این پاسخ رو فوراً ذخیره کن!
        saveResponseToWorkSheet(workSheet, state.currentRound + 1, model, role, 
          result.response, result.tokens, modelTime);
        
        // 🔥 Journal: موفق
        logToJournal(state.promptId, '✅ پاسخ', 
          model + ' (' + modelTime.toFixed(1) + 's, ' + result.tokens + ' توکن)', '✅');
        
        Logger.log('✅ ' + model + ' تکمیل شد (' + modelTime.toFixed(1) + 's)');
      } else {
        // 🔥 Journal: پاسخ خالی
        logToJournal(state.promptId, '⚠️ پاسخ خالی', model, '⚠️');
        
        Logger.log('⚠️ ' + model + ' پاسخ خالی داد');
        updateModelInWorkSheet(workSheet, model, '⚠️ پاسخ خالی');
      }
      
      // 🔥 فقط یک مدل در هر فراخوانی! بعد pause کن
      if (processedInThisCall >= 1) {
        Logger.log('✅ یک مدل پردازش شد - pause برای resume بعدی');
        
        // ذخیره پاسخ‌های جزئی
        state.currentRoundResponses = responses;
        state.currentRoundTokens = tokens;
        state.currentRoundRoles = roles;
        
        // اگه همه مدل‌ها تکمیل شدن، دور کامل شده
        if (completedModels >= state.models.length) {
          // 🔥 Journal: دور کامل
          logToJournal(state.promptId, '🎉 دور کامل', 'دور ' + (state.currentRound + 1) + ' - ' + completedModels + ' مدل', '✅');
          
          Logger.log('🎉 همه مدل‌ها تکمیل شدند - دور تمام');
          
          // پاک کردن state موقت
          delete state.currentRoundResponses;
          delete state.currentRoundTokens;
          delete state.currentRoundRoles;
          
          return {
            success: true,
            roundData: {
              round: state.currentRound + 1,
              responses: responses,
              tokens: tokens,
              roles: roles
            },
            completedModels: completedModels,
            time: (new Date().getTime() - roundStart) / 1000
          };
        }
        
        return {
          success: false,
          partial: true,
          completedModels: completedModels,
          time: (new Date().getTime() - roundStart) / 1000
        };
      }
      
    } catch (error) {
      // 🔥 Journal: خطا
      logToJournal(state.promptId, '❌ خطا', model + ': ' + error.message, '❌');
      
      Logger.log('❌ خطا در ' + model + ': ' + error);
      updateModelInWorkSheet(workSheet, model, '❌ خطا', error.message);
    }
  }
  
  // اگه به اینجا رسید یعنی همه مدل‌ها پردازش شدن
  if (completedModels >= state.models.length) {
    // پاک کردن state موقت
    delete state.currentRoundResponses;
    delete state.currentRoundTokens;
    delete state.currentRoundRoles;
    
    return {
      success: true,
      roundData: {
        round: state.currentRound + 1,
        responses: responses,
        tokens: tokens,
        roles: roles
      },
      completedModels: completedModels,
      time: (new Date().getTime() - roundStart) / 1000
    };
  }
  
  // ذخیره برای دفعه بعد
  state.currentRoundResponses = responses;
  state.currentRoundTokens = tokens;
  state.currentRoundRoles = roles;
  
  return {
    success: false,
    partial: true,
    completedModels: completedModels,
    time: (new Date().getTime() - roundStart) / 1000
  };
}

/**
 * آپدیت وضعیت مدل در Work Sheet
 */
function updateModelInWorkSheet(workSheet, modelId, status, response, tokensUsed, time) {
  try {
    // پیدا کردن ردیف مدل
    for (let i = 1; i <= 8; i++) {
      const row = 5 + i;
      const model = workSheet.getRange(`B${row}`).getValue();
      if (model === modelId) {
        // آپدیت وضعیت
        workSheet.getRange(`E${row}`).setValue(status);
        
        // آپدیت پاسخ (خلاصه)
        if (response) {
          workSheet.getRange(`D${row}`).setValue(response.substring(0, 500) + '...');
        }
        
        // آپدیت توکن
        if (tokensUsed) {
          workSheet.getRange(`F${row}`).setValue(tokensUsed);
        }
        
        // آپدیت زمان
        if (time) {
          workSheet.getRange(`G${row}`).setValue(time.toFixed(1) + 's');
        }
        
        SpreadsheetApp.flush();
        break;
      }
    }
  } catch (e) {
    Logger.log('⚠️ خطا در آپدیت Work Sheet: ' + e);
  }
}

/**
 * 🔥 خواندن پاسخ‌های تکمیل شده از Work Sheet
 */
function readResponsesFromWorkSheet(workSheet, roundNum) {
  const responses = {};
  const tokens = {};
  const sheetName = workSheet.getName();
  
  try {
    Logger.log('📖 خواندن پاسخ‌های دور ' + roundNum + ' از Work Sheet');
    
    // 🔥 خواندن از جدول پاسخ‌ها (ردیف 34+) - نه جدول مدل‌ها!
    for (let i = 0; i < 50; i++) {
      const row = 34 + i;
      const rowRoundNum = workSheet.getRange(`A${row}`).getValue();
      const model = workSheet.getRange(`B${row}`).getValue();
      const responsePreview = workSheet.getRange(`D${row}`).getValue();
      const tokenCount = workSheet.getRange(`F${row}`).getValue();
      const status = workSheet.getRange(`H${row}`).getValue();
      
      // اگه ردیف خالیه، متوقف شو
      if (!model || model === '') break;
      
      // فقط پاسخ‌های همین دور
      if (parseInt(rowRoundNum) === parseInt(roundNum) && status && status.includes('تکمیل')) {
        // خواندن پاسخ کامل از Cache
        const fullResponse = readFullResponseFromCache(sheetName, roundNum, model);
        responses[model] = fullResponse || responsePreview;
        tokens[model] = tokenCount || 0;
        Logger.log('📖 پاسخ دور ' + roundNum + ' یافت شد: ' + model);
      }
    }
    
    Logger.log('📋 تعداد پاسخ‌های یافت شده برای دور ' + roundNum + ': ' + Object.keys(responses).length);
    
  } catch (e) {
    Logger.log('⚠️ خطا در خواندن پاسخ‌ها: ' + e);
  }
  
  return { responses, tokens };
}

/**
 * 🔥 ذخیره پاسخ در Work Sheet و Cache
 */
function saveResponseToWorkSheet(workSheet, roundNum, modelId, role, response, tokensUsed, time) {
  try {
    // 1. آپدیت جدول مدل‌ها
    updateModelInWorkSheet(workSheet, modelId, '✅ تکمیل', response, tokensUsed, time);
    
    // 2. ذخیره پاسخ کامل در Cache (چون Sheet محدودیت 50K کاراکتر داره)
    saveFullResponseToCache(workSheet.getName(), roundNum, modelId, response);
    
    // 3. اضافه کردن به جدول پاسخ‌ها (ردیف 34+)
    try {
      // پیدا کردن اولین ردیف خالی در جدول پاسخ‌ها
      const startRow = 34;
      let targetRow = startRow;
      
      for (let i = 0; i < 50; i++) {
        const existingModel = workSheet.getRange(`B${startRow + i}`).getValue();
        const existingRound = workSheet.getRange(`A${startRow + i}`).getValue();
        
        // اگه همین مدل و دور قبلاً ثبت شده، آپدیت کن
        if (existingModel === modelId && existingRound == roundNum) {
          targetRow = startRow + i;
          break;
        }
        
        // اگه خالیه، اینجا بنویس
        if (!existingModel || existingModel === '') {
          targetRow = startRow + i;
          break;
        }
      }
      
      // نوشتن در جدول
      workSheet.getRange(`A${targetRow}`).setValue(roundNum);
      workSheet.getRange(`B${targetRow}`).setValue(modelId);
      workSheet.getRange(`C${targetRow}`).setValue(role);
      workSheet.getRange(`D${targetRow}`).setValue(response.substring(0, 2000)); // محدود به 2000
      workSheet.getRange(`E${targetRow}`).setValue(response.length);
      workSheet.getRange(`F${targetRow}`).setValue(tokensUsed);
      workSheet.getRange(`G${targetRow}`).setValue(time.toFixed(1) + 's');
      workSheet.getRange(`H${targetRow}`).setValue('✅ تکمیل');
      
    } catch (tableError) {
      Logger.log('⚠️ خطا در جدول پاسخ‌ها: ' + tableError);
    }
    
    SpreadsheetApp.flush();
    Logger.log('💾 پاسخ ' + modelId + ' ذخیره شد');
    
  } catch (e) {
    Logger.log('❌ خطا در ذخیره پاسخ: ' + e);
  }
}

/**
 * ذخیره پاسخ کامل در Cache
 */
function saveFullResponseToCache(sheetName, roundNum, modelId, response) {
  try {
    const cache = CacheService.getScriptCache();
    const key = 'RESP_' + sheetName + '_R' + roundNum + '_' + modelId;
    
    // Cache محدودیت 100KB داره - اگه بزرگتره، truncate کن
    const maxSize = 90000;
    const toSave = response.length > maxSize ? response.substring(0, maxSize) : response;
    
    cache.put(key, toSave, 21600); // 6 ساعت
    Logger.log('💾 پاسخ در Cache: ' + key.substring(0, 50));
  } catch (e) {
    Logger.log('⚠️ خطا در Cache: ' + e);
  }
}

/**
 * خواندن پاسخ کامل از Cache
 */
function readFullResponseFromCache(sheetName, roundNum, modelId) {
  try {
    const cache = CacheService.getScriptCache();
    const key = 'RESP_' + sheetName + '_R' + roundNum + '_' + modelId;
    return cache.get(key);
  } catch (e) {
    Logger.log('⚠️ خطا در خواندن از Cache: ' + e);
    return null;
  }
}

/**
 * محاسبه progress - شامل مدل‌های partial
 */
function calculateProgress(state) {
  const mode = MODES[state.mode] || {};
  const numModels = state.models?.length || 3;
  
  // تعداد کل مراحل = (دورها × مدل‌ها) + scoring + judge + summary + finalize
  let totalSteps = state.totalRounds * numModels;
  if (mode.scoring) totalSteps++;
  if (mode.judge) totalSteps++;
  if (mode.summary) totalSteps++;
  totalSteps++; // finalize
  
  // مراحل تکمیل شده
  let completed = 0;
  
  // دورهای کامل شده
  completed += (state.currentRound || 0) * numModels;
  
  // مدل‌های partial در دور فعلی
  if (state.currentRoundResponses) {
    completed += Object.keys(state.currentRoundResponses).length;
  }
  
  // مراحل بعدی
  if (state.scoringDone) completed++;
  if (state.judgeDone) completed++;
  if (state.summaryDone) completed++;
  if (state.status === QUEUE_STATUS.COMPLETED) completed = totalSteps;
  
  const progress = Math.round((completed / totalSteps) * 100);
  Logger.log(`📊 Progress: ${completed}/${totalSteps} = ${progress}%`);
  
  return progress;
}

/**
 * بازسازی State از Work Sheet
 */
function rebuildStateFromWorkSheet(workSheet, promptId) {
  try {
    Logger.log('🔧 بازسازی State از Work Sheet...');
    
    // خواندن اطلاعات پایه
    const prompt = workSheet.getRange('B1').getValue() || '';
    const mode = workSheet.getRange('F2').getValue() || 'debate_simple';
    const totalRounds = parseInt(workSheet.getRange('D2').getValue()) || 1;
    
    // خواندن مدل‌ها
    const models = [];
    for (let i = 1; i <= 5; i++) {
      const model = workSheet.getRange(`B${5+i}`).getValue();
      if (model && model !== '') {
        models.push(model);
      }
    }
    
    // بازسازی state
    const state = {
      promptId: promptId,
      prompt: prompt,
      mode: mode,
      models: models,
      totalRounds: totalRounds,
      currentRound: 0,
      completedRounds: [],
      status: QUEUE_STATUS.PAUSED,
      startTime: new Date().toISOString(),
      attachments: []
    };
    
    Logger.log('✅ State بازسازی شد');
    Logger.log('  Models: ' + models.join(', '));
    
    return state;
    
  } catch (error) {
    Logger.log('❌ خطا در بازسازی: ' + error);
    return null;
  }
}

function cancelProcess(promptId) {
  try {
    const state = loadState(promptId);
    
    if (state) {
      state.status = QUEUE_STATUS.CANCELLED;
      saveState(state);
    }
    
    // حذف trigger های مرتبط
    deleteAutoResumeTriggers();
    
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * 🆕 دریافت وضعیت پردازش چند بخشی
 */
function getChunkedProcessStatus(promptId) {
  try {
    const state = loadState(promptId);
    
    if (!state) {
      return { success: false, error: 'State یافت نشد' };
    }
    
    return {
      success: true,
      promptId: state.promptId,
      status: state.status,
      currentChunk: state.currentChunkIndex || 0,
      totalChunks: state.chunks ? state.chunks.length : 0,
      currentRound: state.currentRound || 0,
      totalRounds: state.totalRounds || 0,
      resumeCount: state.resumeCount || 0,
      startTime: state.startTime,
      lastResumeTime: state.lastResumeTime,
      error: state.error || null
    };
    
  } catch (error) {
    Logger.log('❌ Error getting status: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * 🆕 دریافت نتیجه نهایی پردازش
 */
function getProcessResult(promptId) {
  try {
    const state = loadState(promptId);
    
    if (!state) {
      return { success: false, error: 'State یافت نشد' };
    }
    
    if (state.status !== QUEUE_STATUS.COMPLETED) {
      return { 
        success: false, 
        error: 'پردازش هنوز کامل نشده',
        status: state.status
      };
    }
    
    // برای پردازش چند بخشی
    if (state.chunks && state.finalResult) {
      return {
        success: true,
        promptId: state.promptId,
        result: state.finalResult,
        chunkResponses: state.chunkResponses,
        totalChunks: state.chunks.length,
        resumeCount: state.resumeCount,
        completedAt: new Date().toISOString()
      };
    }
    
    // برای پردازش عادی
    return {
      success: true,
      promptId: state.promptId,
      rounds: state.completedRounds,
      scoring: state.scoringResult,
      judge: state.judgeResult,
      summary: state.summaryResult
    };
    
  } catch (error) {
    Logger.log('❌ Error getting result: ' + error);
    return { success: false, error: error.message };
  }
}

// ========================================
// بخش 9: توابع آرشیو - اصلاح شده
// ========================================

function getFullArchive() {
  try {
    Logger.log('🔍 getFullArchive() شروع شد - ' + new Date().toISOString());
    
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    const sheet = ss.getSheetByName('پرامپت‌ها');
    
    if (!sheet) {
      Logger.log('❌ Sheet پرامپت‌ها یافت نشد');
      return { 
        success: false, 
        error: 'Sheet "پرامپت‌ها" not found', 
        data: [],
        count: 0,
        timestamp: new Date().toISOString()
      };
    }
    
    const data = sheet.getDataRange().getValues();
    Logger.log('📊 تعداد ردیف‌های خام: ' + data.length);
    
    if (data.length <= 1) {
      Logger.log('ℹ️ Sheet خالی است (فقط header)');
      return { 
        success: true, 
        data: [], 
        count: 0,
        message: 'آرشیو خالی است',
        timestamp: new Date().toISOString()
      };
    }
    
    const headers = data[0];
    const rows = data.slice(1);
    
    Logger.log('📋 Headers: ' + headers.join(', '));
    
    // نام ستون‌ها به فارسی هستند، باید mapping بسازیم
    const headerMap = {
      'تاریخ': 'timestamp',
      'ID': 'promptId',
      'پرامپت': 'prompt',
      'پیوست‌ها': 'attachments',
      'حالت': 'mode',
      'دورها': 'rounds',
      'مدل‌ها': 'models',
      'داور': 'judge',
      'وضعیت': 'status'
    };
    
    const items = rows.map((row, index) => {
      const item = {
        _rowIndex: index,
        _rowNumber: index + 2
      };
      
      headers.forEach((header, colIndex) => {
        const headerStr = header.toString().trim();
        const key = headerMap[headerStr] || headerStr;
        
        let value = row[colIndex];
        
        if (value === null || value === undefined) {
          item[key] = '';
        } else if (value instanceof Date) {
          item[key] = value.toISOString();
        } else if (typeof value === 'object') {
          item[key] = JSON.stringify(value);
        } else {
          item[key] = String(value);
        }
        
        // همچنین نام فارسی را هم ذخیره کن
        item[headerStr] = item[key];
      });
      
      // اطمینان از وجود promptId
      if (!item.promptId && !item.ID) {
        item.promptId = row[1] || ('AUTO_' + Date.now() + '_' + index);
      }
      
      return item;
    });
    
    Logger.log('✅ تعداد آیتم‌های پردازش شده: ' + items.length);
    
    const result = {
      success: true,
      data: items,
      count: items.length,
      timestamp: new Date().toISOString(),
      message: items.length + ' مناظره در آرشیو'
    };
    
    Logger.log('📤 برگشت object با success=true, count=' + result.count);
    
    return result;
    
  } catch (error) {
    Logger.log('❌ خطای شدید در getFullArchive: ' + error.message);
    Logger.log('Stack trace: ' + error.stack);
    
    return {
      success: false,
      error: error.toString(),
      errorMessage: error.message,
      data: [],
      count: 0,
      timestamp: new Date().toISOString()
    };
  }
}

function loadArchiveDetails(promptId) {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    const roundsSheet = ss.getSheetByName('دورهای مناظره');
    const thinkingSheet = ss.getSheetByName('فرآیند تفکر');
    const scoresSheet = ss.getSheetByName('امتیازات');
    const judgeSheet = ss.getSheetByName('داوری');
    
    if (!roundsSheet) return { rounds: [], thinking: [], scores: [], judge: null };
    
    const roundsData = roundsSheet.getDataRange().getValues();
    const rounds = [];
    
    for (let i = 1; i < roundsData.length; i++) {
      if (roundsData[i][0] === promptId) {
        rounds.push({
          round: roundsData[i][1],
          timestamp: roundsData[i][2],
          model: roundsData[i][3],
          response: roundsData[i][4],
          processingTime: roundsData[i][5]
        });
      }
    }
    
    const thinking = [];
    if (thinkingSheet) {
      const thinkingData = thinkingSheet.getDataRange().getValues();
      for (let i = 1; i < thinkingData.length; i++) {
        if (thinkingData[i][1] === promptId) {
          thinking.push({
            timestamp: thinkingData[i][0],
            round: thinkingData[i][2],
            model: thinkingData[i][3],
            stage: thinkingData[i][4],
            thinking: thinkingData[i][5]
          });
        }
      }
    }
    
    const scores = [];
    if (scoresSheet) {
      const scoresData = scoresSheet.getDataRange().getValues();
      for (let i = 1; i < scoresData.length; i++) {
        if (scoresData[i][1] === promptId) {
          scores.push({
            timestamp: scoresData[i][0],
            scorer: scoresData[i][2],
            target: scoresData[i][3],
            accuracy: scoresData[i][4],
            completeness: scoresData[i][5],
            creativity: scoresData[i][6],
            reasoning: scoresData[i][7],
            total: scoresData[i][8]
          });
        }
      }
    }
    
    let judge = null;
    if (judgeSheet) {
      const judgeData = judgeSheet.getDataRange().getValues();
      for (let i = 1; i < judgeData.length; i++) {
        if (judgeData[i][1] === promptId) {
          judge = {
            timestamp: judgeData[i][0],
            judge: judgeData[i][2],
            winner: judgeData[i][3],
            reasoning: judgeData[i][4],
            score: judgeData[i][5],
            fullResponse: judgeData[i][6]
          };
          break;
        }
      }
    }
    
    return { rounds: rounds, thinking: thinking, scores: scores, judge: judge };
    
  } catch (error) {
    Logger.log('خطا در بارگذاری جزئیات: ' + error);
    return { rounds: [], thinking: [], scores: [], judge: null };
  }
}

function getUsageStats() {
  try {
    Logger.log('🔍 getUsageStats() شروع شد - ' + new Date().toISOString());
    
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    
    const stats = {
      totalPrompts: 0,
      completedPrompts: 0,
      pendingPrompts: 0,
      failedPrompts: 0,
      totalRounds: 0,
      totalModels: 0,
      totalTokens: 0,
      totalCost: 0.0,
      avgTime: 0.0,
      avgRoundsPerPrompt: 0.0,
      modelStats: {},
      lastUpdated: new Date().toISOString()
    };
    
    // خواندن پرامپت‌ها
    const promptsSheet = ss.getSheetByName('پرامپت‌ها');
    
    if (promptsSheet) {
      const promptsData = promptsSheet.getDataRange().getValues();
      
      if (promptsData.length > 1) {
        const headers = promptsData[0];
        const rows = promptsData.slice(1);
        
        // پیدا کردن ایندکس ستون‌ها با نام فارسی
        const statusColFa = headers.indexOf('وضعیت');
        const roundsColFa = headers.indexOf('دورها');
        const modelsColFa = headers.indexOf('مدل‌ها');
        
        rows.forEach((row, idx) => {
          try {
            stats.totalPrompts++;
            
            // وضعیت
            const statusCol = statusColFa !== -1 ? statusColFa : 8;
            const status = String(row[statusCol] || '').toLowerCase().trim();
            if (status.includes('تکمیل') || status === 'completed' || status === 'satisfied') {
              stats.completedPrompts++;
            } else if (status.includes('در حال') || status === 'pending' || status === 'processing') {
              stats.pendingPrompts++;
            } else if (status.includes('خطا') || status === 'failed' || status === 'error') {
              stats.failedPrompts++;
            }
            
            // دورها
            const roundsCol = roundsColFa !== -1 ? roundsColFa : 5;
            const roundsVal = parseFloat(row[roundsCol]) || 0;
            stats.totalRounds += roundsVal;
            
            // مدل‌ها
            const modelsCol = modelsColFa !== -1 ? modelsColFa : 6;
            const modelsStr = String(row[modelsCol] || '');
            if (modelsStr) {
              const modelList = modelsStr.split(',').map(m => m.trim()).filter(m => m);
              stats.totalModels += modelList.length;
              
              modelList.forEach(model => {
                const modelKey = model.toLowerCase();
                if (!stats.modelStats[modelKey]) {
                  stats.modelStats[modelKey] = {
                    count: 0,
                    tokens: 0,
                    cost: 0.0
                  };
                }
                stats.modelStats[modelKey].count++;
              });
            }
            
          } catch (rowError) {
            Logger.log('⚠️ خطا در پردازش ردیف ' + (idx + 2) + ': ' + rowError.message);
          }
        });
        
        if (stats.totalPrompts > 0) {
          stats.avgRoundsPerPrompt = parseFloat((stats.totalRounds / stats.totalPrompts).toFixed(2));
        }
      }
    }
    
    // خواندن مصرف توکن
    const usageSheet = ss.getSheetByName('مصرف توکن');
    
    if (usageSheet) {
      const usageData = usageSheet.getDataRange().getValues();
      
      if (usageData.length > 1) {
        const headers = usageData[0];
        const rows = usageData.slice(1);
        
        // پیدا کردن ایندکس ستون‌ها
        const modelColFa = headers.indexOf('مدل');
        const tokensColFa = headers.indexOf('توکن');
        const costColFa = headers.indexOf('هزینه تقریبی');
        
        const modelCol = modelColFa !== -1 ? modelColFa : 2;
        const tokensCol = tokensColFa !== -1 ? tokensColFa : 3;
        const costCol = costColFa !== -1 ? costColFa : 4;
        
        rows.forEach((row, idx) => {
          try {
            const model = String(row[modelCol] || 'unknown').toLowerCase().trim();
            const tokens = parseFloat(row[tokensCol]) || 0;
            let cost = 0;
            
            const costStr = String(row[costCol] || '0');
            // 🔥 اصلاح: حذف همه کاراکترهای غیرعددی (به جز نقطه و منفی)
            cost = parseFloat(costStr.replace(/[^\d.-]/g, '')) || 0;
            
            stats.totalTokens += tokens;
            stats.totalCost += cost;
            
            if (!stats.modelStats[model]) {
              stats.modelStats[model] = {
                count: 0,
                tokens: 0,
                cost: 0.0
              };
            }
            
            stats.modelStats[model].tokens += tokens;
            stats.modelStats[model].cost += cost;
            
          } catch (rowError) {
            Logger.log('⚠️ خطا در پردازش مصرف ردیف ' + (idx + 2) + ': ' + rowError.message);
          }
        });
      }
    }
    
    // گرد کردن مقادیر
    stats.totalCost = parseFloat(stats.totalCost.toFixed(4));
    stats.avgTime = 30; // مقدار پیش‌فرض
    
    Object.keys(stats.modelStats).forEach(model => {
      stats.modelStats[model].cost = parseFloat(stats.modelStats[model].cost.toFixed(4));
    });
    
    Logger.log('📤 آمار نهایی: prompts=' + stats.totalPrompts + ', models=' + Object.keys(stats.modelStats).length);
    
    return {
      success: true,
      stats: stats,
      timestamp: new Date().toISOString()
    };
    
  } catch (error) {
    Logger.log('❌ خطای شدید در getUsageStats: ' + error.message);
    
    return {
      success: false,
      error: error.toString(),
      stats: {
        totalPrompts: 0,
        completedPrompts: 0,
        totalRounds: 0,
        totalModels: 0,
        totalTokens: 0,
        totalCost: 0.0,
        avgTime: 0.0,
        modelStats: {}
      },
      timestamp: new Date().toISOString()
    };
  }
}

function getScoringStats() {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    const sheet = ss.getSheetByName('امتیازات');
    
    if (!sheet) return { averages: {}, totalScores: 0 };
    
    const data = sheet.getDataRange().getValues();
    if (data.length <= 1) return { averages: {}, totalScores: 0 };
    
    const modelScores = {};
    
    for (let i = 1; i < data.length; i++) {
      const target = data[i][3];
      const total = Number(data[i][8]) || 0;
      
      if (!modelScores[target]) {
        modelScores[target] = [];
      }
      
      modelScores[target].push(total);
    }
    
    const averages = {};
    Object.keys(modelScores).forEach(model => {
      const scores = modelScores[model];
      const sum = scores.reduce((a, b) => a + b, 0);
      averages[model] = Math.round(sum / scores.length);
    });
    
    return {
      averages: averages,
      totalScores: data.length - 1
    };
    
  } catch (error) {
    Logger.log('خطا در آمار امتیازات: ' + error);
    return { error: error.message };
  }
}

function getJudgeStats() {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    const sheet = ss.getSheetByName('داوری');
    
    if (!sheet) return { totalJudgements: 0, byJudge: {}, byWinner: {} };
    
    const data = sheet.getDataRange().getValues();
    if (data.length <= 1) return { totalJudgements: 0, byJudge: {}, byWinner: {} };
    
    const byJudge = {};
    const byWinner = {};
    
    for (let i = 1; i < data.length; i++) {
      const judge = data[i][2];
      const winner = data[i][3];
      const score = Number(data[i][5]) || 0;
      
      if (!byJudge[judge]) {
        byJudge[judge] = { count: 0, avgScore: 0, scores: [] };
      }
      
      byJudge[judge].count++;
      byJudge[judge].scores.push(score);
      
      if (!byWinner[winner]) {
        byWinner[winner] = 0;
      }
      
      byWinner[winner]++;
    }
    
    Object.keys(byJudge).forEach(judge => {
      const scores = byJudge[judge].scores;
      const sum = scores.reduce((a, b) => a + b, 0);
      byJudge[judge].avgScore = Math.round(sum / scores.length);
      delete byJudge[judge].scores;
    });
    
    return {
      totalJudgements: data.length - 1,
      byJudge: byJudge,
      byWinner: byWinner
    };
    
  } catch (error) {
    Logger.log('خطا در آمار داوری: ' + error);
    return { error: error.message };
  }
}

// ========================================
// بخش 10: استخراج محتوای فایل
// ========================================

function extractFileContent(attachments) {
  if (!attachments || attachments.length === 0) return '';
  
  let extractedText = '\n\n--- محتوای فایل‌های پیوست ---\n';
  
  for (let idx = 0; idx < attachments.length; idx++) {
    try {
      const file = attachments[idx];
      const fileName = file.name || 'فایل ' + (idx + 1);
      const mimeType = file.mimeType || '';
      let data = file.data || '';
      
      // حذف prefix از base64 data
      if (data && data.includes(',')) {
        data = data.split(',')[1];
      }
      
      Logger.log('📎 ' + fileName + ' (' + mimeType + ')');
      
      const fileExt = fileName.split('.').pop().toLowerCase();
      
      // تصاویر - فقط tag اضافه می‌کنیم، داده‌ها جداگانه ارسال می‌شوند
      if (mimeType.startsWith('image/')) {
        extractedText += '\n[تصویر: ' + fileName + ' - این تصویر به مدل‌های vision ارسال شده است]\n';
        continue;
      }
      
      // PDF
      if (mimeType === 'application/pdf' || fileExt === 'pdf') {
        try {
          const blob = Utilities.newBlob(Utilities.base64Decode(data), mimeType, fileName);
          const pdfText = extractTextFromPDF(blob);
          if (pdfText) {
            extractedText += '\n--- ' + fileName + ' ---\n' + pdfText + '\n';
            Logger.log('✅ PDF: ' + pdfText.length + ' chars');
          }
        } catch (e) {
          Logger.log('⚠️ PDF: ' + e.message);
          extractedText += '\n[PDF: ' + fileName + ' - خطا در خواندن]\n';
        }
        continue;
      }
      
      // فایل‌های متنی ساده
      const textExtensions = ['txt', 'md', 'markdown', 'rtf', 'log'];
      if (mimeType.includes('text') || textExtensions.includes(fileExt)) {
        try {
          const textContent = Utilities.newBlob(Utilities.base64Decode(data)).getDataAsString();
          extractedText += '\n--- ' + fileName + ' ---\n' + textContent + '\n';
          Logger.log('✅ Text: ' + textContent.length + ' chars');
        } catch (e) {
          Logger.log('⚠️ Text: ' + e.message);
        }
        continue;
      }
      
      // فایل‌های کد
      const codeExtensions = ['js', 'ts', 'py', 'java', 'cpp', 'c', 'h', 'cs', 'go', 'rs', 'rb', 
                              'php', 'swift', 'kt', 'html', 'css', 'scss', 'less', 'sql', 'sh', 
                              'bash', 'ps1', 'vue', 'jsx', 'tsx', 'gs', 'gas'];
      if (codeExtensions.includes(fileExt)) {
        try {
          const codeContent = Utilities.newBlob(Utilities.base64Decode(data)).getDataAsString();
          
          // 🔥 محدودیت حجم: حداکثر 50,000 کاراکتر برای هر فایل
          const MAX_CODE_LENGTH = 50000;
          let truncatedContent = codeContent;
          let truncated = false;
          
          if (codeContent.length > MAX_CODE_LENGTH) {
            truncatedContent = codeContent.substring(0, MAX_CODE_LENGTH);
            truncated = true;
            Logger.log('⚠️ Code truncated: ' + codeContent.length + ' → ' + MAX_CODE_LENGTH + ' chars');
          }
          
          extractedText += '\n--- ' + fileName + ' (کد' + (truncated ? ' - کوتاه‌شده' : '') + ') ---\n```' + fileExt + '\n' + truncatedContent + '\n```\n';
          
          if (truncated) {
            extractedText += '\n[⚠️ فایل ' + fileName + ' بزرگ‌تر از ' + MAX_CODE_LENGTH + ' کاراکتر بود و کوتاه شد. حجم اصلی: ' + codeContent.length + ' کاراکتر]\n';
          }
          
          Logger.log('✅ Code: ' + truncatedContent.length + ' chars' + (truncated ? ' (truncated)' : ''));
        } catch (e) {
          Logger.log('⚠️ Code: ' + e.message);
        }
        continue;
      }
      
      // JSON
      if (mimeType.includes('json') || fileExt === 'json') {
        try {
          const jsonContent = Utilities.newBlob(Utilities.base64Decode(data)).getDataAsString();
          extractedText += '\n--- ' + fileName + ' ---\n```json\n' + jsonContent + '\n```\n';
          Logger.log('✅ JSON: ' + jsonContent.length + ' chars');
        } catch (e) {
          Logger.log('⚠️ JSON: ' + e.message);
        }
        continue;
      }
      
      // CSV
      if (mimeType.includes('csv') || fileExt === 'csv') {
        try {
          const csvContent = Utilities.newBlob(Utilities.base64Decode(data)).getDataAsString();
          extractedText += '\n--- ' + fileName + ' (CSV) ---\n' + csvContent.substring(0, 5000) + '\n';
          Logger.log('✅ CSV: ' + csvContent.length + ' chars');
        } catch (e) {
          Logger.log('⚠️ CSV: ' + e.message);
        }
        continue;
      }
      
      // XML / YAML
      if (['xml', 'yaml', 'yml'].includes(fileExt)) {
        try {
          const content = Utilities.newBlob(Utilities.base64Decode(data)).getDataAsString();
          extractedText += '\n--- ' + fileName + ' ---\n```' + fileExt + '\n' + content + '\n```\n';
          Logger.log('✅ ' + fileExt.toUpperCase() + ': ' + content.length + ' chars');
        } catch (e) {
          Logger.log('⚠️ ' + fileExt + ': ' + e.message);
        }
        continue;
      }
      
      // Word Documents
      if (mimeType.includes('word') || ['docx', 'doc'].includes(fileExt)) {
        try {
          const blob = Utilities.newBlob(Utilities.base64Decode(data), mimeType, fileName);
          const wordText = extractTextFromWord(blob);
          if (wordText) {
            extractedText += '\n--- ' + fileName + ' ---\n' + wordText + '\n';
            Logger.log('✅ Word: ' + wordText.length + ' chars');
          }
        } catch (e) {
          Logger.log('⚠️ Word: ' + e.message);
          extractedText += '\n[Word: ' + fileName + ' - خطا در خواندن]\n';
        }
        continue;
      }
      
      // Excel
      if (mimeType.includes('spreadsheet') || mimeType.includes('excel') || ['xlsx', 'xls'].includes(fileExt)) {
        try {
          const blob = Utilities.newBlob(Utilities.base64Decode(data), mimeType, fileName);
          const excelText = extractTextFromExcel(blob);
          if (excelText) {
            extractedText += '\n--- ' + fileName + ' (Excel) ---\n' + excelText + '\n';
            Logger.log('✅ Excel: ' + excelText.length + ' chars');
          }
        } catch (e) {
          Logger.log('⚠️ Excel: ' + e.message);
          extractedText += '\n[Excel: ' + fileName + ' - خطا در خواندن]\n';
        }
        continue;
      }
      
      // PowerPoint
      if (mimeType.includes('presentation') || ['pptx', 'ppt'].includes(fileExt)) {
        extractedText += '\n[پاورپوینت: ' + fileName + ' - لطفاً به PDF تبدیل کنید]\n';
        continue;
      }
      
      // آرشیو
      if (['zip', 'rar', '7z', 'tar', 'gz'].includes(fileExt)) {
        extractedText += '\n[آرشیو: ' + fileName + ' - لطفاً فایل‌ها را استخراج کنید]\n';
        continue;
      }
      
      extractedText += '\n[فایل: ' + fileName + ' (' + mimeType + ') - پشتیبانی نمی‌شود]\n';
      
    } catch (error) {
      Logger.log('❌ خطا فایل ' + idx + ': ' + error.message);
    }
  }
  
  extractedText += '--- پایان فایل‌ها ---\n\n';
  return extractedText;
}

// استخراج متن از Word با OCR
function extractTextFromWord(blob) {
  try {
    const folder = DriveApp.getFolderById(CONFIG.folderId);
    const file = folder.createFile(blob);
    
    // تبدیل به Google Doc
    const resource = { 
      title: file.getName().replace(/\.(docx?|rtf|odt)$/i, ''), 
      mimeType: 'application/vnd.google-apps.document' 
    };
    
    const docFile = Drive.Files.copy(resource, file.getId());
    const doc = DocumentApp.openById(docFile.id);
    const text = doc.getBody().getText();
    
    // پاکسازی
    DriveApp.getFileById(file.getId()).setTrashed(true);
    DriveApp.getFileById(docFile.id).setTrashed(true);
    
    return text.substring(0, 10000); // حداکثر 10000 کاراکتر
  } catch (error) {
    Logger.log('⚠️ Word extraction: ' + error.message);
    return null;
  }
}

// استخراج متن از Excel
function extractTextFromExcel(blob) {
  try {
    const folder = DriveApp.getFolderById(CONFIG.folderId);
    const file = folder.createFile(blob);
    
    // تبدیل به Google Sheet
    const resource = { 
      title: file.getName().replace(/\.(xlsx?|ods)$/i, ''), 
      mimeType: 'application/vnd.google-apps.spreadsheet' 
    };
    
    const sheetFile = Drive.Files.copy(resource, file.getId());
    const ss = SpreadsheetApp.openById(sheetFile.id);
    
    let text = '';
    const sheets = ss.getSheets();
    
    for (let i = 0; i < Math.min(sheets.length, 3); i++) { // حداکثر 3 شیت
      const sheet = sheets[i];
      const data = sheet.getDataRange().getValues();
      text += '\n[شیت: ' + sheet.getName() + ']\n';
      
      for (let row = 0; row < Math.min(data.length, 50); row++) { // حداکثر 50 سطر
        text += data[row].join('\t') + '\n';
      }
    }
    
    // پاکسازی
    DriveApp.getFileById(file.getId()).setTrashed(true);
    DriveApp.getFileById(sheetFile.id).setTrashed(true);
    
    return text.substring(0, 10000);
  } catch (error) {
    Logger.log('⚠️ Excel extraction: ' + error.message);
    return null;
  }
}

function extractTextFromPDF(blob) {
  try {
    const folder = DriveApp.getFolderById(CONFIG.folderId);
    const file = folder.createFile(blob);
    
    const resource = { title: file.getName(), mimeType: 'application/vnd.google-apps.document' };
    const options = { ocr: true, ocrLanguage: 'fa,en' };
    
    const docFile = Drive.Files.copy(resource, file.getId(), options);
    const doc = DocumentApp.openById(docFile.id);
    const text = doc.getBody().getText();
    
    DriveApp.getFileById(file.getId()).setTrashed(true);
    DriveApp.getFileById(docFile.id).setTrashed(true);
    
    return text.substring(0, 5000);
  } catch (error) {
    Logger.log('⚠️ OCR: ' + error.message);
    return null;
  }
}

// ========================================
// بخش 11: خلاصه‌نویس - اصلاح شده
// ========================================

function generateSummarySimple(promptId, prompt, summarizerModel, allContent) {
  Logger.log('\n📝 خلاصه‌نویس: ' + summarizerModel);
  
  try {
    // ✅ v17.2: افزایش طول prompt و content برای خلاصه بهتر
    const summaryPrompt = SUMMARY_PROMPT
      .replace('{prompt}', prompt.substring(0, 1500))       // ✅ از 300 به 1500
      .replace('{allContent}', allContent.substring(0, 8000)); // ✅ از 3000 به 8000
    
    const originalMax = CONFIG.maxTokensPerModel;
    CONFIG.maxTokensPerModel = CONFIG.maxTokensForSummary;
    
    const result = callModel(summarizerModel, summaryPrompt, []);
    
    CONFIG.maxTokensPerModel = originalMax;
    
    const summary = parseSummaryResponse(result.response);
    
    Logger.log('✅ خلاصه تولید شد');
    
    return {
      summarizer: summarizerModel,
      summary: summary,
      fullText: result.response,
      tokens: result.tokens
    };
    
  } catch (error) {
    Logger.log('❌ خلاصه: ' + error.message);
    return null;
  }
}

function parseSummaryResponse(response) {
  const summary = {
    general: '',
    keyPoints: [],
    conclusion: '',
    winner: ''
  };
  
  try {
    const generalMatch = response.match(/خلاصه کلی.*?[:：]\s*([^\n]+(?:\n(?!###)[^\n]+)*)/i);
    if (generalMatch) summary.general = generalMatch[1].trim();
    
    const keyPointsMatch = response.match(/نکات کلیدی.*?[:：]([\s\S]*?)(?:###|$)/i);
    if (keyPointsMatch) {
      const lines = keyPointsMatch[1].split('\n').filter(l => l.trim().startsWith('-'));
      summary.keyPoints = lines.map(l => l.replace(/^-\s*/, '').trim());
    }
    
    const conclusionMatch = response.match(/نتیجه.*?گیری.*?[:：]\s*([^\n]+(?:\n(?!###)[^\n]+)*)/i);
    if (conclusionMatch) summary.conclusion = conclusionMatch[1].trim();
    
    const winnerMatch = response.match(/برنده.*?[:：]\s*([^\n]+)/i);
    if (winnerMatch) summary.winner = winnerMatch[1].trim();
    
  } catch (error) {
    Logger.log('⚠️ Parse: ' + error);
  }
  
  return summary;
}

// ========================================
// بخش 12: FRONTEND API ENDPOINTS
// ========================================

/**
 * 🆕 تخمین حجم درخواست قبل از ارسال
 * این تابع از Frontend فراخوانی می‌شود تا هشدار نمایش دهد
 */
function estimateRequestSize(prompt, attachments) {
  try {
    const promptTokens = Math.ceil((prompt || '').length / 4);
    const fileTokens = estimateTokens(attachments || []);
    const totalTokens = promptTokens + fileTokens;
    
    // تعیین مدل‌های مناسب بر اساس حجم
    const suitableModels = [];
    const keys = getApiKeys();
    
    for (const [id, model] of Object.entries(MODEL_REGISTRY)) {
      if (!model.enabled || !keys[model.provider]) continue;
      
      const contextWindow = model.contextWindow || 0;
      
      // مدل باید حداقل 1.5 برابر توکن‌ها context داشته باشد
      if (contextWindow >= totalTokens * 1.5) {
        suitableModels.push({
          id: id,
          name: model.name,
          provider: model.provider,
          contextWindow: contextWindow,
          headroom: contextWindow - totalTokens
        });
      }
    }
    
    // مرتب‌سازی بر اساس context window
    suitableModels.sort((a, b) => b.contextWindow - a.contextWindow);
    
    // تعیین وضعیت
    let status = 'ok';
    let message = '';
    
    if (totalTokens > 100000) {
      status = 'critical';
      message = 'حجم درخواست خیلی زیاد است (' + Math.round(totalTokens/1000) + 'K توکن). فقط Gemini می‌تواند پردازش کند.';
    } else if (totalTokens > 25000) {
      status = 'warning';
      message = 'حجم درخواست زیاد است (' + Math.round(totalTokens/1000) + 'K توکن). برخی مدل‌ها محدودیت دارند.';
    } else {
      status = 'ok';
      message = 'حجم درخواست مناسب است.';
    }
    
    return {
      success: true,
      promptTokens: promptTokens,
      fileTokens: fileTokens,
      totalTokens: totalTokens,
      status: status,
      message: message,
      suitableModels: suitableModels.slice(0, 5),
      recommendedModel: suitableModels.length > 0 ? suitableModels[0].id : null
    };
    
  } catch (error) {
    Logger.log('❌ Error in estimateRequestSize: ' + error);
    return {
      success: false,
      error: error.toString(),
      totalTokens: 0,
      status: 'unknown'
    };
  }
}

function getAvailableModels() {
  try {
    const keys = getApiKeys();
    let allModels = [];
    
    // 1. مدل‌های ثابت از MODEL_REGISTRY
    const staticModels = Object.keys(MODEL_REGISTRY).map(key => {
      const model = MODEL_REGISTRY[key];
      const hasApiKey = !!keys[model.provider];
      
      return {
        id: String(key),
        name: String(model.name || key),
        provider: String(model.provider || 'unknown'),
        capabilities: Array.isArray(model.capabilities) ? model.capabilities.map(String) : ['text'],
        strengths: Array.isArray(model.strengths) ? model.strengths.map(String) : [],
        enabled: Boolean(model.enabled && hasApiKey),
        hasApiKey: Boolean(hasApiKey),
        priority: Number(model.priority) || 99,
        costPer1kTokens: Number(model.costPer1kTokens) || 0,
        supportsImages: Boolean(model.supportsImages),
        contextWindow: Number(model.contextWindow) || 4096,
        isImageGenerator: Boolean(model.isImageGenerator),
        discovered: false,
        dynamic: false,
        supportsWebFetch: true
      };
    });
    
    allModels = [...staticModels];
    
    // 2. مدل‌های داینامیک از OpenRouter
    if (keys.openrouter) {
      try {
        const openRouterModels = fetchOpenRouterModels(keys.openrouter);
        if (openRouterModels.length > 0) {
          Logger.log('✅ OpenRouter: ' + openRouterModels.length + ' models loaded');
          allModels = [...allModels, ...openRouterModels];
        }
      } catch (e) {
        Logger.log('⚠️ OpenRouter models fetch failed: ' + e);
      }
    }
    
    // 3. مدل‌های داینامیک از Groq
    if (keys.groq) {
      try {
        const groqModels = fetchGroqModels(keys.groq);
        if (groqModels.length > 0) {
          Logger.log('✅ Groq: ' + groqModels.length + ' models loaded');
          allModels = [...allModels, ...groqModels];
        }
      } catch (e) {
        Logger.log('⚠️ Groq models fetch failed: ' + e);
      }
    }
    
    // حذف تکراری‌ها (بر اساس id)
    const uniqueModels = [];
    const seenIds = new Set();
    for (const model of allModels) {
      if (!seenIds.has(model.id)) {
        seenIds.add(model.id);
        uniqueModels.push(model);
      }
    }
    
    const providers = [...new Set(uniqueModels.map(m => m.provider))];
    
    return {
      success: true,
      models: uniqueModels,
      providers: providers,
      totalCount: uniqueModels.length,
      enabledCount: uniqueModels.filter(m => m.enabled).length,
      dynamicCount: uniqueModels.filter(m => m.dynamic).length,
      webFetchEnabled: true,
      timestamp: new Date().toISOString()
    };
    
  } catch (error) {
    Logger.log('❌ Error in getAvailableModels: ' + error);
    return {
      success: false,
      error: error.toString(),
      models: [],
      providers: []
    };
  }
}

/**
 * ✅ v17.1.5: دریافت فقط مدل‌های فعال
 * @returns {Array} لیست مدل‌های فعال شده
 */
function getEnabledModels() {
  try {
    const result = getAvailableModels();
    if (!result.success || !result.models) {
      return [];
    }
    
    // فیلتر کردن فقط مدل‌های فعال
    const enabledModels = result.models.filter(m => m.enabled === true);
    
    // مرتب‌سازی بر اساس اولویت
    enabledModels.sort((a, b) => (a.priority || 99) - (b.priority || 99));
    
    return enabledModels;
    
  } catch (error) {
    Logger.log('⚠️ Error in getEnabledModels: ' + error);
    return [];
  }
}

/**
 * ✅ v17.1.5: دریافت مدل فعلی پیش‌فرض
 * @returns {string} شناسه مدل پیش‌فرض
 */
function getCurrentModel() {
  try {
    const enabledModels = getEnabledModels();
    if (enabledModels.length > 0) {
      return enabledModels[0].id;
    }
    return 'gpt-4-turbo'; // fallback
  } catch (error) {
    return 'gpt-4-turbo';
  }
}

/**
 * دریافت مدل‌های OpenRouter از API
 */
function fetchOpenRouterModels(apiKey) {
  try {
    const response = UrlFetchApp.fetch('https://openrouter.ai/api/v1/models', {
      method: 'get',
      headers: { 'Authorization': 'Bearer ' + apiKey },
      muteHttpExceptions: true
    });
    
    if (response.getResponseCode() !== 200) {
      Logger.log('⚠️ OpenRouter API error: ' + response.getResponseCode());
      return [];
    }
    
    const data = JSON.parse(response.getContentText());
    if (!data.data) return [];
    
    // فقط مدل‌های معتبر و محبوب رو برگردون (حداکثر 50 تا)
    const models = data.data
      .filter(m => m.id && !m.id.includes('free')) // حذف مدل‌های رایگان با کیفیت پایین
      .slice(0, 50) // حداکثر 50 مدل
      .map(m => ({
        id: String(m.id),
        name: String(m.name || m.id),
        provider: 'openrouter',
        capabilities: ['text'],
        strengths: [],
        enabled: true,
        hasApiKey: true,
        priority: 50,
        costPer1kTokens: m.pricing ? (parseFloat(m.pricing.prompt) || 0) * 1000 : 0,
        supportsImages: false,
        contextWindow: Number(m.context_length) || 4096,
        isImageGenerator: false,
        discovered: true,
        dynamic: true,
        supportsWebFetch: true
      }));
    
    return models;
  } catch (e) {
    Logger.log('❌ fetchOpenRouterModels error: ' + e);
    return [];
  }
}

/**
 * دریافت مدل‌های Groq از API
 */
function fetchGroqModels(apiKey) {
  try {
    const response = UrlFetchApp.fetch('https://api.groq.com/openai/v1/models', {
      method: 'get',
      headers: { 'Authorization': 'Bearer ' + apiKey },
      muteHttpExceptions: true
    });
    
    if (response.getResponseCode() !== 200) {
      Logger.log('⚠️ Groq API error: ' + response.getResponseCode());
      return [];
    }
    
    const data = JSON.parse(response.getContentText());
    if (!data.data) return [];
    
    const models = data.data.map(m => ({
      id: String(m.id),
      name: String(m.id).replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
      provider: 'groq',
      capabilities: ['text', 'fast-response'],
      strengths: ['speed'],
      enabled: true,
      hasApiKey: true,
      priority: 30,
      costPer1kTokens: 0.0001, // Groq خیلی ارزان است
      supportsImages: false,
      contextWindow: Number(m.context_window) || 8192,
      isImageGenerator: false,
      discovered: true,
      dynamic: true,
      supportsWebFetch: true
    }));
    
    return models;
  } catch (e) {
    Logger.log('❌ fetchGroqModels error: ' + e);
    return [];
  }
}

/**
 * دریافت و به‌روزرسانی لیست مدل‌ها 
 * توجه: کشف داینامیک فعلاً غیرفعال است
 */
function refreshModels() {
  try {
    Logger.log('🔄 Refreshing models list...');
    
    // فقط لیست مدل‌های موجود رو برگردون
    // کشف داینامیک فعلاً غیرفعال چون مشکل serialize داره
    const result = getAvailableModels();
    
    Logger.log('  ✅ Models: ' + (result.models ? result.models.length : 0));
    
    return result;
    
  } catch (error) {
    Logger.log('❌ Error in refreshModels: ' + error);
    return {
      success: false,
      error: error.toString(),
      models: [],
      providers: []
    };
  }
}

/**
 * انتخاب خودکار مدل‌ها بر اساس نوع فایل‌های پیوست و پرامپت
 * @param {string} prompt - پرامپت کاربر
 * @param {Array} attachments - لیست فایل‌های پیوست
 * @param {string} mode - حالت انتخاب شده
 * @returns {Object} - لیست مدل‌های پیشنهادی
 */
// Wrapper برای سازگاری - از تابع پیشرفته‌تر استفاده می‌کند
function smartSelectModels(prompt, attachments, mode) {
  return smartSelectModelsAdvanced(prompt, attachments, mode);
}

// این تابع برای سازگاری حفظ شده
function getModelReason(model, analysis) {
  const reasons = [];
  
  if (analysis.hasImages && model.supportsImages) reasons.push('پشتیبانی تصویر');
  if (analysis.isCodeTask && model.id.includes('coder')) reasons.push('تخصص کدنویسی');
  if (analysis.isCreative && model.provider === 'claude') reasons.push('خلاقیت بالا');
  if (analysis.isResearch && model.id.includes('pro')) reasons.push('تحلیل عمیق');
  if (analysis.isQuick && model.id.includes('flash')) reasons.push('سرعت بالا');
  
  if (model.provider === 'gemini') reasons.push('هزینه کم');
  
  return reasons.length > 0 ? reasons.join('، ') : 'مدل عمومی';
}

function toggleModel(modelId, enabled) {
  try {
    if (!MODEL_REGISTRY[modelId]) {
      return {
        success: false,
        error: 'Model not found: ' + modelId
      };
    }
    
    MODEL_REGISTRY[modelId].enabled = enabled;
    
    Logger.log(`✅ Model ${modelId} is now ${enabled ? 'enabled' : 'disabled'}`);
    
    return {
      success: true,
      message: `Model ${modelId} is now ${enabled ? 'enabled' : 'disabled'}`,
      model: {
        id: modelId,
        name: MODEL_REGISTRY[modelId].name,
        enabled: enabled
      }
    };
    
  } catch (error) {
    Logger.log('❌ Error in toggleModel: ' + error);
    return {
      success: false,
      error: error.toString()
    };
  }
}

function updateModelPriority(modelId, priority) {
  try {
    if (!MODEL_REGISTRY[modelId]) {
      return {
        success: false,
        error: 'Model not found: ' + modelId
      };
    }
    
    MODEL_REGISTRY[modelId].priority = parseInt(priority);
    
    Logger.log(`✅ Model ${modelId} priority updated to ${priority}`);
    
    return {
      success: true,
      message: `Model ${modelId} priority updated to ${priority}`,
      model: {
        id: modelId,
        name: MODEL_REGISTRY[modelId].name,
        priority: parseInt(priority)
      }
    };
    
  } catch (error) {
    Logger.log('❌ Error in updateModelPriority: ' + error);
    return {
      success: false,
      error: error.toString()
    };
  }
}

// Alias برای سازگاری با Frontend
function getDebateDetails(promptId) {
  return loadArchiveDetails(promptId);
}

// ========================================
// بخش 13: تست
// ========================================

function TEST_ApiKeys() {
  const keys = getApiKeys();
  const results = {};
  
  Object.keys(keys).forEach(provider => {
    results[provider] = {
      exists: !!keys[provider],
      length: keys[provider] ? keys[provider].length : 0,
      preview: keys[provider] ? keys[provider].substring(0, 10) + '...' : 'NOT_FOUND'
    };
  });
  
  Logger.log('🔑 API Keys Test Results:');
  Logger.log(JSON.stringify(results, null, 2));
  
  return results;
}

function TEST_ModelSelection() {
  Logger.log('🧪 Testing Model Selection...\n');
  
  const testModels = ['gpt4', 'claude', 'deepseek', 'gemini'];
  
  testModels.forEach(model => {
    const resolved = resolveModelId(model);
    Logger.log(`${model} -> ${resolved}`);
  });
  
  Logger.log('✅ Tests completed');
}

function quickTest() {
  Logger.log('🧪 تست سریع v10.0 FIXED...\n');
  
  const result = startProcess(
    'Python یا JavaScript کدام بهتر است؟',
    [],
    ['gemini-2.0-flash', 'deepseek-chat'],
    'QUICK',
    1,
    null
  );
  
  Logger.log('\n📊 نتیجه:');
  Logger.log(JSON.stringify(result, null, 2));
  
  return result;
}
// ========================================
// 🔄 DYNAMIC MODEL MANAGER v1.0
// مدیریت داینامیک API Keys و مدل‌ها
// ========================================

/**
 * تعریف Provider ها و endpoint های آنها
 */
const PROVIDERS = {
  openai: {
    name: 'OpenAI',
    icon: '🟢',
    modelsEndpoint: 'https://api.openai.com/v1/models',
    chatEndpoint: 'https://api.openai.com/v1/chat/completions',
    authHeader: 'Authorization',
    authPrefix: 'Bearer ',
    // فیلتر مدل‌های چت (نه embedding یا whisper)
    modelFilter: (model) => {
      const chatModels = ['gpt-4', 'gpt-3.5', 'o1', 'o3'];
      return chatModels.some(prefix => model.id.includes(prefix)) && 
             !model.id.includes('instruct') &&
             !model.id.includes('realtime');
    },
    // تبدیل پاسخ API به فرمت استاندارد
    parseModels: (response) => {
      if (!response.data) return [];
      return response.data
        .filter(m => PROVIDERS.openai.modelFilter(m))
        .map(m => ({
          id: m.id,
          name: m.id.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
          provider: 'openai',
          created: m.created,
          supportsVision: m.id.includes('vision') || m.id.includes('4o') || m.id.includes('o1')
        }))
        .sort((a, b) => (b.created || 0) - (a.created || 0));
    }
  },
  
  claude: {
    name: 'Anthropic Claude',
    icon: '🟠',
    // Claude API لیست مدل ندارد - لیست ثابت
    modelsEndpoint: null,
    chatEndpoint: 'https://api.anthropic.com/v1/messages',
    authHeader: 'x-api-key',
    authPrefix: '',
    // لیست ثابت مدل‌های Claude (آپدیت دستی)
    staticModels: [
      { id: 'claude-sonnet-4-20250514', name: 'Claude Sonnet 4', tier: 'flagship' },
      { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', tier: 'flagship' },
      { id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku', tier: 'fast' },
      { id: 'claude-3-haiku-20240307', name: 'Claude 3 Haiku', tier: 'fast' }
    ],
    parseModels: (response) => {
      // برای Claude از لیست ثابت استفاده می‌کنیم
      return PROVIDERS.claude.staticModels.map(m => ({
        ...m,
        provider: 'claude',
        supportsVision: true
      }));
    }
  },
  
  gemini: {
    name: 'Google Gemini',
    icon: '🔵',
    modelsEndpoint: 'https://generativelanguage.googleapis.com/v1beta/models',
    chatEndpoint: 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
    authHeader: null, // از query param استفاده می‌کند
    authParam: 'key',
    modelFilter: (model) => {
      return model.name.includes('gemini') && 
             model.supportedGenerationMethods?.includes('generateContent');
    },
    parseModels: (response) => {
      if (!response.models) return [];
      return response.models
        .filter(m => PROVIDERS.gemini.modelFilter(m))
        .map(m => ({
          id: m.name.replace('models/', ''),
          name: m.displayName || m.name.replace('models/', ''),
          provider: 'gemini',
          description: m.description,
          inputTokenLimit: m.inputTokenLimit,
          outputTokenLimit: m.outputTokenLimit,
          supportsVision: m.name.includes('vision') || m.name.includes('pro') || m.name.includes('flash')
        }));
    }
  },
  
  deepseek: {
    name: 'DeepSeek',
    icon: '🟣',
    modelsEndpoint: 'https://api.deepseek.com/models',
    chatEndpoint: 'https://api.deepseek.com/chat/completions',
    authHeader: 'Authorization',
    authPrefix: 'Bearer ',
    // لیست ثابت (API ممکن است کار نکند)
    staticModels: [
      { id: 'deepseek-chat', name: 'DeepSeek Chat', tier: 'general' },
      { id: 'deepseek-coder', name: 'DeepSeek Coder', tier: 'code' },
      { id: 'deepseek-reasoner', name: 'DeepSeek Reasoner', tier: 'reasoning' }
    ],
    parseModels: (response) => {
      if (response && response.data) {
        return response.data.map(m => ({
          id: m.id,
          name: m.id.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
          provider: 'deepseek'
        }));
      }
      // Fallback به لیست ثابت
      return PROVIDERS.deepseek.staticModels.map(m => ({
        ...m,
        provider: 'deepseek'
      }));
    }
  },
  
  groq: {
    name: 'Groq',
    icon: '⚡',
    modelsEndpoint: 'https://api.groq.com/openai/v1/models',
    chatEndpoint: 'https://api.groq.com/openai/v1/chat/completions',
    authHeader: 'Authorization',
    authPrefix: 'Bearer ',
    parseModels: (response) => {
      if (!response.data) return [];
      return response.data.map(m => ({
        id: m.id,
        name: m.id.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        provider: 'groq',
        contextWindow: m.context_window
      }));
    }
  },
  
  openrouter: {
    name: 'OpenRouter',
    icon: '🌐',
    modelsEndpoint: 'https://openrouter.ai/api/v1/models',
    chatEndpoint: 'https://openrouter.ai/api/v1/chat/completions',
    authHeader: 'Authorization',
    authPrefix: 'Bearer ',
    parseModels: (response) => {
      if (!response.data) return [];
      return response.data.map(m => ({
        id: m.id,
        name: m.name || m.id,
        provider: 'openrouter',
        contextLength: m.context_length,
        pricing: m.pricing
      }));
    }
  }
};

// ========================================
// 🔑 API KEY MANAGEMENT
// ========================================

/**
 * ذخیره API Key برای یک Provider
 */
function saveApiKey(provider, apiKey) {
  try {
    if (!PROVIDERS[provider]) {
      return { success: false, error: `Provider نامعتبر: ${provider}` };
    }
    
    const props = PropertiesService.getScriptProperties();
    const keyName = `${provider.toUpperCase()}_API_KEY`;
    
    if (apiKey && apiKey.trim()) {
      props.setProperty(keyName, apiKey.trim());
      Logger.log(`✅ API Key saved for ${provider}`);
      return { success: true, message: `کلید ${PROVIDERS[provider].name} ذخیره شد` };
    } else {
      props.deleteProperty(keyName);
      Logger.log(`🗑️ API Key removed for ${provider}`);
      return { success: true, message: `کلید ${PROVIDERS[provider].name} حذف شد` };
    }
  } catch (error) {
    Logger.log(`❌ Error saving API key: ${error}`);
    return { success: false, error: error.toString() };
  }
}

/**
 * دریافت همه API Keys (masked برای امنیت)
 */
function getApiKeyStatus() {
  try {
    const props = PropertiesService.getScriptProperties();
    const status = {};
    
    for (const provider of Object.keys(PROVIDERS)) {
      const keyName = `${provider.toUpperCase()}_API_KEY`;
      const key = props.getProperty(keyName);
      
      status[provider] = {
        name: PROVIDERS[provider].name,
        icon: PROVIDERS[provider].icon,
        hasKey: !!key,
        maskedKey: key ? maskApiKey(key) : null,
        modelsEndpoint: !!PROVIDERS[provider].modelsEndpoint
      };
    }
    
    return { success: true, data: status };
  } catch (error) {
    Logger.log(`❌ Error getting API key status: ${error}`);
    return { success: false, error: error.toString() };
  }
}

/**
 * Mask کردن API Key برای نمایش
 */
function maskApiKey(key) {
  if (!key || key.length < 8) return '****';
  return key.substring(0, 4) + '****' + key.substring(key.length - 4);
}

/**
 * تست اعتبار API Key
 */
function testApiKey(provider, apiKey) {
  try {
    if (!PROVIDERS[provider]) {
      return { success: false, error: `Provider نامعتبر: ${provider}` };
    }
    
    const config = PROVIDERS[provider];
    const key = apiKey || getApiKey(provider);
    
    if (!key) {
      return { success: false, error: 'کلید API موجود نیست' };
    }
    
    // تست با یک درخواست ساده
    if (provider === 'claude') {
      // تست Claude با یک پیام ساده
      return testClaudeKey(key);
    } else if (provider === 'gemini') {
      // تست Gemini
      return testGeminiKey(key);
    } else {
      // برای بقیه، تلاش برای گرفتن لیست مدل‌ها
      const models = fetchModelsFromApi(provider, key);
      if (models.success && models.data.length > 0) {
        return { 
          success: true, 
          message: `✅ کلید معتبر است - ${models.data.length} مدل یافت شد`,
          modelsCount: models.data.length
        };
      } else {
        return { success: false, error: models.error || 'کلید نامعتبر است' };
      }
    }
  } catch (error) {
    Logger.log(`❌ Error testing API key: ${error}`);
    return { success: false, error: error.toString() };
  }
}

function testClaudeKey(apiKey) {
  try {
    const response = UrlFetchApp.fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01'
      },
      payload: JSON.stringify({
        model: 'claude-3-haiku-20240307',
        max_tokens: 10,
        messages: [{ role: 'user', content: 'Hi' }]
      }),
      muteHttpExceptions: true
    });
    
    const code = response.getResponseCode();
    if (code === 200) {
      return { success: true, message: '✅ کلید Claude معتبر است' };
    } else if (code === 401) {
      return { success: false, error: 'کلید نامعتبر است' };
    } else {
      const data = JSON.parse(response.getContentText());
      return { success: false, error: data.error?.message || `خطا: ${code}` };
    }
  } catch (error) {
    return { success: false, error: error.toString() };
  }
}

function testGeminiKey(apiKey) {
  try {
    const url = `https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}`;
    const response = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    
    const code = response.getResponseCode();
    if (code === 200) {
      const data = JSON.parse(response.getContentText());
      return { 
        success: true, 
        message: `✅ کلید Gemini معتبر است - ${data.models?.length || 0} مدل`,
        modelsCount: data.models?.length || 0
      };
    } else {
      return { success: false, error: 'کلید نامعتبر است' };
    }
  } catch (error) {
    return { success: false, error: error.toString() };
  }
}

// ========================================
// 📋 DYNAMIC MODEL FETCHING
// ========================================

/**
 * دریافت لیست مدل‌ها از یک Provider
 */
function fetchModelsFromApi(provider, apiKey) {
  try {
    const config = PROVIDERS[provider];
    if (!config) {
      return { success: false, error: `Provider نامعتبر: ${provider}` };
    }
    
    const key = apiKey || getApiKey(provider);
    if (!key) {
      return { success: false, error: 'کلید API موجود نیست', data: [] };
    }
    
    // اگر endpoint ندارد (مثل Claude)، از لیست ثابت استفاده کن
    if (!config.modelsEndpoint) {
      const models = config.parseModels({});
      return { success: true, data: models, source: 'static' };
    }
    
    // ساخت URL
    let url = config.modelsEndpoint;
    if (config.authParam) {
      url += `?${config.authParam}=${key}`;
    }
    
    // ساخت headers
    const headers = { 'Content-Type': 'application/json' };
    if (config.authHeader) {
      headers[config.authHeader] = (config.authPrefix || '') + key;
    }
    
    // درخواست
    const response = UrlFetchApp.fetch(url, {
      method: 'GET',
      headers: headers,
      muteHttpExceptions: true
    });
    
    const code = response.getResponseCode();
    if (code !== 200) {
      Logger.log(`⚠️ API returned ${code} for ${provider}`);
      // Fallback به لیست ثابت اگر موجود باشد
      if (config.staticModels) {
        return { 
          success: true, 
          data: config.staticModels.map(m => ({ ...m, provider })), 
          source: 'static-fallback' 
        };
      }
      return { success: false, error: `خطای API: ${code}`, data: [] };
    }
    
    const data = JSON.parse(response.getContentText());
    const models = config.parseModels(data);
    
    Logger.log(`✅ Fetched ${models.length} models from ${provider}`);
    return { success: true, data: models, source: 'api' };
    
  } catch (error) {
    Logger.log(`❌ Error fetching models from ${provider}: ${error}`);
    
    // Fallback به لیست ثابت
    const config = PROVIDERS[provider];
    if (config?.staticModels) {
      return { 
        success: true, 
        data: config.staticModels.map(m => ({ ...m, provider })), 
        source: 'static-error-fallback' 
      };
    }
    
    return { success: false, error: error.toString(), data: [] };
  }
}

/**
 * دریافت همه مدل‌های موجود از تمام Provider های فعال
 */
function getAllAvailableModels() {
  try {
    const allModels = [];
    const props = PropertiesService.getScriptProperties();
    
    for (const provider of Object.keys(PROVIDERS)) {
      const keyName = `${provider.toUpperCase()}_API_KEY`;
      const key = props.getProperty(keyName);
      
      if (key) {
        const result = fetchModelsFromApi(provider, key);
        if (result.success && result.data) {
          // اضافه کردن اطلاعات Provider به هر مدل
          const modelsWithProvider = result.data.map(m => ({
            ...m,
            providerName: PROVIDERS[provider].name,
            providerIcon: PROVIDERS[provider].icon,
            source: result.source
          }));
          allModels.push(...modelsWithProvider);
        }
      }
    }
    
    // گروه‌بندی بر اساس Provider
    const grouped = {};
    for (const model of allModels) {
      if (!grouped[model.provider]) {
        grouped[model.provider] = {
          name: model.providerName,
          icon: model.providerIcon,
          models: []
        };
      }
      grouped[model.provider].models.push(model);
    }
    
    return { 
      success: true, 
      data: {
        all: allModels,
        grouped: grouped,
        count: allModels.length
      }
    };
    
  } catch (error) {
    Logger.log(`❌ Error getting all models: ${error}`);
    return { success: false, error: error.toString() };
  }
}

/**
 * پیشنهاد بهترین مدل‌ها بر اساس نوع پرامپت
 */
function suggestModelsForPrompt(prompt, taskType) {
  try {
    const allModels = getAllAvailableModels();
    if (!allModels.success) {
      return { success: false, error: allModels.error };
    }
    
    const models = allModels.data.all;
    const suggestions = [];
    
    // تحلیل پرامپت
    const promptLower = prompt.toLowerCase();
    const isCode = /کد|برنامه|code|python|javascript|programming|function|api/i.test(prompt);
    const isCreative = /داستان|شعر|خلاق|creative|story|poem|write/i.test(prompt);
    const isResearch = /تحقیق|بررسی|تحلیل|research|analyze|compare/i.test(prompt);
    const isImage = /تصویر|عکس|image|picture|visual/i.test(prompt);
    const isLong = prompt.length > 1000;
    
    // امتیازدهی به مدل‌ها
    for (const model of models) {
      let score = 50; // امتیاز پایه
      
      // بر اساس نوع task
      if (isCode) {
        if (model.id.includes('coder') || model.id.includes('code')) score += 30;
        if (model.id.includes('gpt-4') || model.id.includes('claude')) score += 20;
        if (model.id.includes('deepseek')) score += 15;
      }
      
      if (isCreative) {
        if (model.id.includes('claude') || model.id.includes('gpt-4')) score += 25;
        if (model.id.includes('sonnet') || model.id.includes('opus')) score += 20;
      }
      
      if (isResearch) {
        if (model.id.includes('pro') || model.id.includes('opus')) score += 25;
        if (model.id.includes('gpt-4') || model.id.includes('claude')) score += 20;
        if (model.id.includes('o1') || model.id.includes('reasoner')) score += 30;
      }
      
      if (isImage && model.supportsVision) {
        score += 30;
      }
      
      if (isLong) {
        if (model.id.includes('gemini')) score += 20; // context بزرگ
        if (model.id.includes('claude')) score += 15;
      }
      
      // تنوع Provider
      const providerBonus = {
        openai: 10,
        claude: 10,
        gemini: 5,
        deepseek: 5,
        groq: 5
      };
      score += providerBonus[model.provider] || 0;
      
      suggestions.push({
        ...model,
        score: score,
        reason: getSelectionReason(model, { isCode, isCreative, isResearch, isImage, isLong })
      });
    }
    
    // مرتب‌سازی و انتخاب بهترین‌ها
    suggestions.sort((a, b) => b.score - a.score);
    
    // حداقل 2 مدل از Provider های مختلف
    const selected = [];
    const usedProviders = new Set();
    
    for (const model of suggestions) {
      if (selected.length >= 4) break;
      
      // اگر هنوز از این Provider نداریم یا امتیاز خیلی بالاست
      if (!usedProviders.has(model.provider) || model.score > 70) {
        selected.push(model);
        usedProviders.add(model.provider);
      }
    }
    
    return {
      success: true,
      data: {
        suggested: selected,
        all: suggestions.slice(0, 10),
        analysis: { isCode, isCreative, isResearch, isImage, isLong }
      }
    };
    
  } catch (error) {
    Logger.log(`❌ Error suggesting models: ${error}`);
    return { success: false, error: error.toString() };
  }
}

function getSelectionReason(model, analysis) {
  const reasons = [];
  
  if (analysis.isCode && (model.id.includes('coder') || model.id.includes('code'))) {
    reasons.push('مناسب کدنویسی');
  }
  if (analysis.isCreative && model.id.includes('claude')) {
    reasons.push('خلاقیت بالا');
  }
  if (analysis.isResearch && (model.id.includes('o1') || model.id.includes('pro'))) {
    reasons.push('استدلال قوی');
  }
  if (analysis.isImage && model.supportsVision) {
    reasons.push('پشتیبانی تصویر');
  }
  if (analysis.isLong && model.id.includes('gemini')) {
    reasons.push('context بزرگ');
  }
  
  return reasons.length > 0 ? reasons.join('، ') : 'مدل عمومی';
}

// ========================================
// 🔧 HELPER FUNCTIONS
// ========================================

/**
 * دریافت API Key یک Provider
 */
function getApiKey(provider) {
  try {
    const props = PropertiesService.getScriptProperties();
    const keyName = `${provider.toUpperCase()}_API_KEY`;
    return props.getProperty(keyName);
  } catch (error) {
    Logger.log(`❌ Error getting API key for ${provider}: ${error}`);
    return null;
  }
}

/**
 * لیست Provider های پشتیبانی شده
 */
function getSupportedProviders() {
  return {
    success: true,
    data: Object.keys(PROVIDERS).map(key => ({
      id: key,
      name: PROVIDERS[key].name,
      icon: PROVIDERS[key].icon,
      hasDynamicModels: !!PROVIDERS[key].modelsEndpoint
    }))
  };
}

/**
 * رفرش کردن کش مدل‌ها
 */
function refreshModelsCache() {
  try {
    const cache = CacheService.getScriptCache();
    const result = getAllAvailableModels();
    
    if (result.success) {
      // ذخیره در کش برای 1 ساعت
      cache.put('ALL_MODELS', JSON.stringify(result.data), 3600);
      return { success: true, message: 'کش مدل‌ها آپدیت شد', count: result.data.count };
    }
    
    return result;
  } catch (error) {
    return { success: false, error: error.toString() };
  }
}

/**
 * دریافت مدل‌ها از کش (سریع‌تر)
 */
function getCachedModels() {
  try {
    const cache = CacheService.getScriptCache();
    const cached = cache.get('ALL_MODELS');
    
    if (cached) {
      return { success: true, data: JSON.parse(cached), source: 'cache' };
    }
    
    // اگر کش خالی بود، از API بگیر و کش کن
    return refreshModelsCache();
  } catch (error) {
    return getAllAvailableModels();
  }
}

// ========================================
// 📥 توابع EXPORT و دریافت پاسخ‌های کامل
// ========================================

/**
 * دریافت پاسخ‌های کامل یک پردازش از Sheet
 */
function getFullResponses(promptId) {
  try {
    Logger.log('📥 دریافت پاسخ‌های کامل: ' + promptId);
    
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    const sheet = ss.getSheetByName('دورهای مناظره');
    
    if (!sheet) {
      return { success: false, error: 'Sheet دورها پیدا نشد' };
    }
    
    const data = sheet.getDataRange().getValues();
    const headers = data[0];
    const idIndex = headers.indexOf('ID پرامپت');
    
    const responses = [];
    
    for (let i = 1; i < data.length; i++) {
      if (data[i][idIndex] === promptId) {
        responses.push({
          round: data[i][1],
          timestamp: data[i][2],
          model: data[i][3],
          response: data[i][4],  // پاسخ کامل
          processingTime: data[i][5]
        });
      }
    }
    
    Logger.log('✅ ' + responses.length + ' پاسخ پیدا شد');
    
    return {
      success: true,
      promptId: promptId,
      responses: responses,
      count: responses.length
    };
    
  } catch (error) {
    Logger.log('❌ خطا: ' + error);
    return { success: false, error: error.toString() };
  }
}

/**
 * Export کامل یک پردازش به Google Doc
 */
function exportToDoc(promptId) {
  try {
    Logger.log('📄 Export به Doc: ' + promptId);
    
    // دریافت اطلاعات
    const responses = getFullResponses(promptId);
    if (!responses.success) {
      return responses;
    }
    
    // دریافت پرامپت
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    const promptSheet = ss.getSheetByName('پرامپت‌ها');
    let promptText = '';
    let mode = '';
    
    if (promptSheet) {
      const data = promptSheet.getDataRange().getValues();
      for (let i = 1; i < data.length; i++) {
        if (data[i][0] === promptId) {
          promptText = data[i][2];
          mode = data[i][4];
          break;
        }
      }
    }
    
    // ایجاد Doc
    const folder = DriveApp.getFolderById(CONFIG.folderId);
    const docName = '📋 Export_' + promptId.substring(3, 18);
    const doc = DocumentApp.create(docName);
    const body = doc.getBody();
    
    // عنوان
    body.appendParagraph('🎯 گزارش پردازش AI')
        .setHeading(DocumentApp.ParagraphHeading.HEADING1);
    
    body.appendParagraph('شناسه: ' + promptId);
    body.appendParagraph('حالت: ' + mode);
    body.appendParagraph('تاریخ: ' + new Date().toLocaleString('fa-IR'));
    body.appendHorizontalRule();
    
    // پرامپت
    body.appendParagraph('📝 پرامپت:')
        .setHeading(DocumentApp.ParagraphHeading.HEADING2);
    body.appendParagraph(promptText || '(پرامپت یافت نشد)');
    body.appendHorizontalRule();
    
    // پاسخ‌ها
    body.appendParagraph('💬 پاسخ‌های مدل‌ها:')
        .setHeading(DocumentApp.ParagraphHeading.HEADING2);
    
    responses.responses.forEach(r => {
      body.appendParagraph(`🔄 دور ${r.round} - ${r.model}`)
          .setHeading(DocumentApp.ParagraphHeading.HEADING3);
      body.appendParagraph(r.response || '(پاسخ خالی)');
      body.appendParagraph('⏱️ زمان: ' + r.processingTime + 's');
      body.appendHorizontalRule();
    });
    
    // انتقال به پوشه
    const file = DriveApp.getFileById(doc.getId());
    folder.addFile(file);
    DriveApp.getRootFolder().removeFile(file);
    
    doc.saveAndClose();
    
    Logger.log('✅ Doc ایجاد شد: ' + doc.getUrl());
    
    return {
      success: true,
      docId: doc.getId(),
      docUrl: doc.getUrl(),
      docName: docName
    };
    
  } catch (error) {
    Logger.log('❌ خطا در export: ' + error);
    return { success: false, error: error.toString() };
  }
}

/**
 * Export به فایل متنی
 */
function exportToText(promptId) {
  try {
    Logger.log('📄 Export به Text: ' + promptId);
    
    const responses = getFullResponses(promptId);
    if (!responses.success) {
      return responses;
    }
    
    // ساخت محتوای متنی
    let content = '═══════════════════════════════════════════════\n';
    content += '🎯 گزارش پردازش AI\n';
    content += '═══════════════════════════════════════════════\n\n';
    content += 'شناسه: ' + promptId + '\n';
    content += 'تاریخ: ' + new Date().toLocaleString('fa-IR') + '\n';
    content += 'تعداد پاسخ‌ها: ' + responses.count + '\n\n';
    
    responses.responses.forEach(r => {
      content += '───────────────────────────────────────────────\n';
      content += `🔄 دور ${r.round} | ${r.model} | ${r.processingTime}s\n`;
      content += '───────────────────────────────────────────────\n\n';
      content += r.response + '\n\n';
    });
    
    content += '═══════════════════════════════════════════════\n';
    content += '✅ پایان گزارش\n';
    
    // ایجاد فایل
    const folder = DriveApp.getFolderById(CONFIG.folderId);
    const fileName = 'Export_' + promptId.substring(3, 18) + '.txt';
    const file = folder.createFile(fileName, content, 'text/plain');
    
    Logger.log('✅ فایل ایجاد شد: ' + file.getUrl());
    
    return {
      success: true,
      fileId: file.getId(),
      fileUrl: file.getUrl(),
      fileName: fileName,
      content: content
    };
    
  } catch (error) {
    Logger.log('❌ خطا: ' + error);
    return { success: false, error: error.toString() };
  }
}

/**
 * ذخیره پاسخ‌های کامل در Work Sheet (در sheet جدا)
 */
function saveFullResponsesToWorkSheet(promptId, completedRounds) {
  try {
    Logger.log('📥 saveFullResponsesToWorkSheet: ' + promptId);
    Logger.log('📊 completedRounds: ' + (completedRounds ? completedRounds.length : 'null') + ' دور');
    
    // 🔥 Debug: نمایش محتوای completedRounds
    if (completedRounds) {
      completedRounds.forEach((round, idx) => {
        const responseCount = round.responses ? Object.keys(round.responses).length : 0;
        Logger.log('  📋 دور ' + round.round + ': ' + responseCount + ' پاسخ');
      });
    }
    
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    const sheetName = '📄 Full_' + promptId.substring(3, 18);
    
    // حذف اگر وجود داره
    let existingSheet = ss.getSheetByName(sheetName);
    if (existingSheet) {
      ss.deleteSheet(existingSheet);
    }
    
    // ایجاد sheet جدید
    const sheet = ss.insertSheet(sheetName);
    
    // هدر
    sheet.getRange('A1:F1').setValues([['دور', 'مدل', 'نقش', 'زمان', 'توکن', 'پاسخ کامل']]);
    sheet.getRange('A1:F1').setBackground('#4caf50').setFontColor('#ffffff').setFontWeight('bold');
    
    // 🔥 اگه completedRounds خالیه، لاگ بزن و return کن
    if (!completedRounds || completedRounds.length === 0) {
      Logger.log('⚠️ completedRounds خالیه! نمی‌توان پاسخ‌ها را ذخیره کرد');
      sheet.getRange('A2').setValue('⚠️ پاسخی یافت نشد');
      return { success: false, error: 'completedRounds خالی است' };
    }
    
    let row = 2;
    let totalResponses = 0;
    
    completedRounds.forEach(round => {
      if (!round.responses || Object.keys(round.responses).length === 0) {
        Logger.log('⚠️ دور ' + round.round + ' بدون پاسخ');
        return;
      }
      
      Object.entries(round.responses).forEach(([model, response]) => {
        const role = round.roles?.[model] || model;
        const tokens = round.tokens?.[model] || 0;
        
        sheet.getRange(`A${row}:F${row}`).setValues([[
          round.round,
          model,
          role,
          round.processingTime?.toFixed(1) + 's',
          tokens,
          response  // پاسخ کامل!
        ]]);
        
        // تنظیم ارتفاع سطر برای متن طولانی
        sheet.setRowHeight(row, 200);
        
        row++;
        totalResponses++;
      });
    });
    
    Logger.log('✅ ' + totalResponses + ' پاسخ ذخیره شد در Full Sheet');
    
    // تنظیم عرض ستون پاسخ
    sheet.setColumnWidth(6, 800);
    
    // Wrap text
    sheet.getRange('F:F').setWrap(true);
    
    // رنگ تب
    sheet.setTabColor('#4caf50');
    
    Logger.log('✅ پاسخ‌های کامل در Sheet ذخیره شدند: ' + sheetName);
    
    return { success: true, sheetName: sheetName, totalResponses: totalResponses };
    
  } catch (error) {
    Logger.log('❌ خطا در saveFullResponsesToWorkSheet: ' + error);
    return { success: false, error: error.toString() };
  }
}

// ========================================
// 📦 PROJECT MANAGEMENT - مدیریت پروژه
// ========================================

// فولدر آرشیو نهایی
const ARCHIVE_FOLDER_ID = '1bx1_rQKjIu6fNzkSMcb8RuT5HMlyI_j1';

/**
 * ادامه پردازش با سوال جدید
 */
function continueProject(promptId, newQuestion, newAttachments) {
  try {
    Logger.log('\n' + '='.repeat(60));
    Logger.log('🔄 ادامه پروژه: ' + promptId);
    Logger.log('  سوال جدید: ' + (newQuestion || '').substring(0, 100) + '...');
    Logger.log('  فایل‌های جدید: ' + (newAttachments?.length || 0));
    Logger.log('='.repeat(60));
    
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    const idPart = promptId.substring(3, 18); // بخش اصلی شناسه
    
    // پیدا کردن Work Sheet اصلی
    const workSheet = findWorkSheet(promptId);
    if (!workSheet) {
      throw new Error('Work Sheet یافت نشد');
    }
    
    // خواندن اطلاعات قبلی
    const originalPrompt = workSheet.getRange('B1').getValue();
    const mode = workSheet.getRange('F2').getValue() || 'collaboration';
    
    // خواندن مدل‌ها از جدول مدل‌ها (ردیف‌های 7-11)
    const models = [];
    for (let i = 1; i <= 5; i++) {
      const model = workSheet.getRange(`B${6+i}`).getValue();
      if (model && model !== '') {
        models.push(model);
      }
    }
    
    if (models.length === 0) {
      // fallback به مدل‌های پیش‌فرض
      models.push('claude-sonnet-4-20250514', 'gpt-4-turbo', 'gpt-4o');
    }
    
    Logger.log('🤖 مدل‌ها: ' + models.join(', '));
    
    // خواندن پاسخ‌های قبلی از جدول پاسخ‌ها (ردیف 34+)
    let previousResponses = [];
    for (let row = 34; row <= 60; row++) {
      const model = workSheet.getRange(`B${row}`).getValue();
      const response = workSheet.getRange(`D${row}`).getValue();
      if (!model || model === '') break;
      if (response) {
        previousResponses.push({ model, response: response.substring(0, 3000) });
      }
    }
    
    // شمارش تعداد ادامه‌ها (بر اساس idPart)
    let continuationCount = 0;
    const sheets = ss.getSheets();
    sheets.forEach(s => {
      const name = s.getName();
      if (name.includes('CONT-') && name.includes(idPart.substring(0, 10))) {
        continuationCount++;
      }
    });
    continuationCount++;
    
    Logger.log('📊 شماره ادامه: ' + continuationCount);
    
    // ========================================
    // ثبت سوال جدید در Work Sheet اصلی
    // ========================================
    const lastRow = workSheet.getLastRow();
    const contStartRow = lastRow + 3;
    
    // هدر ادامه
    workSheet.getRange(contStartRow, 1, 1, 9).setValues([[
      '🔄 ادامه #' + continuationCount, 
      new Date().toLocaleString('fa-IR'), 
      '', '', '', '', '', '', ''
    ]]);
    workSheet.getRange(contStartRow, 1, 1, 9).merge().setBackground('#ff9800').setFontColor('#fff').setFontWeight('bold');
    
    // سوال جدید
    workSheet.getRange(contStartRow + 1, 1, 1, 9).setValues([[
      '❓ سوال جدید:', newQuestion, '', '', '', '', '', '', ''
    ]]);
    workSheet.getRange(contStartRow + 1, 1, 1, 9).setBackground('#fff3e0');
    
    // هدر پاسخ‌ها
    workSheet.getRange(contStartRow + 2, 1, 1, 8).setValues([[
      '#', 'مدل', 'نقش', 'پاسخ', 'طول', 'توکن', 'زمان', 'وضعیت'
    ]]);
    workSheet.getRange(contStartRow + 2, 1, 1, 8).setBackground('#2196f3').setFontColor('#fff').setFontWeight('bold');
    
    SpreadsheetApp.flush();
    
    // ========================================
    // ساخت context prompt
    // ========================================
    let contextPrompt = `## سوال اصلی:
${originalPrompt}

## پاسخ‌های قبلی:
${previousResponses.map(r => `### ${r.model}:\n${r.response}`).join('\n\n')}

## سوال/ابهام جدید کاربر:
${newQuestion}

لطفاً با توجه به سوال اصلی، پاسخ‌های قبلی، و سوال جدید کاربر، پاسخ کامل و جامع ارائه دهید.
`;
    
    // اضافه کردن محتوای فایل‌های جدید
    if (newAttachments && newAttachments.length > 0) {
      contextPrompt += '\n\n## فایل‌های جدید پیوست شده:\n';
      newAttachments.forEach(att => {
        if (att.content) {
          contextPrompt += `### ${att.name}:\n${att.content.substring(0, 5000)}\n\n`;
        }
      });
    }
    
    // ========================================
    // فراخوانی مدل‌ها و ذخیره پاسخ‌ها
    // ========================================
    const responses = [];
    let responseRow = contStartRow + 3;
    
    for (let i = 0; i < models.length; i++) {
      const modelId = models[i];
      
      // آپدیت وضعیت
      workSheet.getRange(`A${responseRow + i}`).setValue(i + 1);
      workSheet.getRange(`B${responseRow + i}`).setValue(modelId);
      workSheet.getRange(`H${responseRow + i}`).setValue('⏳ در حال پردازش...');
      SpreadsheetApp.flush();
      
      try {
        const startTime = Date.now();
        
        // فراخوانی مدل
        const result = callModel(modelId, contextPrompt, null);
        
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
        
        if (result.success) {
          const response = result.response || '';
          const tokens = result.tokens || 0;
          
          responses.push({
            model: modelId,
            response: response,
            tokens: tokens,
            time: elapsed
          });
          
          // ذخیره در Work Sheet
          workSheet.getRange(`D${responseRow + i}`).setValue(response.substring(0, 50000));
          workSheet.getRange(`E${responseRow + i}`).setValue(response.length);
          workSheet.getRange(`F${responseRow + i}`).setValue(tokens);
          workSheet.getRange(`G${responseRow + i}`).setValue(elapsed + 's');
          workSheet.getRange(`H${responseRow + i}`).setValue('✅ تکمیل');
          workSheet.getRange(responseRow + i, 8).setBackground('#c8e6c9');
          
          Logger.log(`  ✅ ${modelId}: ${response.length} chars, ${tokens} tokens`);
          
        } else {
          workSheet.getRange(`H${responseRow + i}`).setValue('❌ خطا: ' + (result.error || 'نامشخص'));
          workSheet.getRange(responseRow + i, 8).setBackground('#ffcdd2');
          Logger.log(`  ❌ ${modelId}: ${result.error}`);
        }
        
      } catch (e) {
        workSheet.getRange(`H${responseRow + i}`).setValue('❌ خطا: ' + e.message);
        workSheet.getRange(responseRow + i, 8).setBackground('#ffcdd2');
        Logger.log(`  ❌ ${modelId}: ${e.message}`);
      }
      
      SpreadsheetApp.flush();
    }
    
    // ========================================
    // ثبت در شیت پرامپت‌ها (با شناسه اصلی)
    // ========================================
    const promptSheet = ss.getSheetByName('پرامپت‌ها');
    if (promptSheet) {
      promptSheet.appendRow([
        promptId + '-CONT-' + continuationCount, // شناسه با رابطه به اصلی
        new Date().toLocaleString('fa-IR'),
        newQuestion.substring(0, 1000),
        'ادامه #' + continuationCount + ' از: ' + promptId,
        mode,
        models.join(', '),
        '✅ تکمیل'
      ]);
    }
    
    // آپدیت وضعیت Work Sheet
    workSheet.getRange('H1').setValue('🔄 ادامه #' + continuationCount + ' - ' + new Date().toLocaleString('fa-IR'));
    
    Logger.log('✅ ادامه پروژه تکمیل شد');
    Logger.log('  📊 ' + responses.length + ' پاسخ دریافت شد');
    
    return {
      success: true,
      promptId: promptId, // همان شناسه اصلی
      continuationNumber: continuationCount,
      responsesCount: responses.length,
      responses: responses.map(r => ({
        model: r.model,
        preview: (r.response || '').substring(0, 500),
        tokens: r.tokens
      }))
    };
    
  } catch (error) {
    Logger.log('❌ خطا در ادامه پروژه: ' + error);
    Logger.log('  Stack: ' + error.stack);
    return { success: false, error: error.message };
  }
}

/**
 * بستن پروژه و آرشیو کامل
 */
function closeProject(promptId) {
  try {
    Logger.log('\n' + '='.repeat(60));
    Logger.log('📦 بستن و آرشیو پروژه: ' + promptId);
    Logger.log('='.repeat(60));
    
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    const idPart = promptId.substring(3, 18);
    const shortId = promptId.substring(3, 11);
    
    // ========================================
    // 1. پیدا کردن همه شیت‌های مرتبط
    // ========================================
    const relatedSheets = [];
    const sheets = ss.getSheets();
    
    sheets.forEach(sheet => {
      const name = sheet.getName();
      // الگوهای مختلف نام شیت‌ها
      if (name.includes(idPart) ||                    // Work_1764911416440
          name.includes(shortId) ||                   // حاوی شناسه کوتاه
          name.startsWith('🔧 Work_' + idPart) ||     // Work Sheet
          name.startsWith('✅ Done_' + idPart) ||     // Done Sheet
          name.startsWith('📄 Full_' + idPart) ||     // Full Responses
          name.startsWith('CONT-' + shortId) ||       // Continuation sheets
          name.startsWith('CONT-AI_' + shortId)) {    // Continuation با AI_
        relatedSheets.push(sheet);
        Logger.log('  📋 شیت پیدا شد: ' + name);
      }
    });
    
    if (relatedSheets.length === 0) {
      throw new Error('هیچ شیت مرتبطی پیدا نشد');
    }
    
    Logger.log('📋 تعداد شیت‌های مرتبط: ' + relatedSheets.length);
    
    // ========================================
    // 2. خواندن اطلاعات اصلی پروژه
    // ========================================
    const mainSheet = relatedSheets.find(s => 
      s.getName().includes('Work_') || s.getName().includes('Done_')
    ) || relatedSheets[0];
    
    const originalPrompt = mainSheet.getRange('B1').getValue() || 'پرامپت نامشخص';
    const mode = mainSheet.getRange('F2').getValue() || 'collaboration';
    const startTime = mainSheet.getRange('H2').getValue() || new Date().toLocaleString('fa-IR');
    
    // ========================================
    // 3. ایجاد فولدر آرشیو
    // ========================================
    const promptSummary = generateFolderName(originalPrompt);
    const dateStr = Utilities.formatDate(new Date(), 'Asia/Tehran', 'yyyy-MM-dd_HH-mm');
    const folderName = `${promptId}_${dateStr}_${promptSummary}`;
    
    Logger.log('📁 نام فولدر: ' + folderName);
    
    const archiveParent = DriveApp.getFolderById(ARCHIVE_FOLDER_ID);
    const projectFolder = archiveParent.createFolder(folderName);
    const projectFolderId = projectFolder.getId();
    
    Logger.log('📁 فولدر ایجاد شد: ' + projectFolderId);
    
    // ========================================
    // 4. جمع‌آوری محتوای کامل برای Markdown مفصل
    // ========================================
    let fullMarkdown = `# 🤖 آرشیو کامل پروژه AI Debate System

================================================================================
                           گزارش جامع پردازش هوش مصنوعی
================================================================================

## 📋 اطلاعات کلی پروژه

| عنوان | مقدار |
|-------|-------|
| 🆔 شناسه پروژه | \`${promptId}\` |
| 📅 تاریخ شروع | ${startTime} |
| 📅 تاریخ آرشیو | ${new Date().toLocaleString('fa-IR')} |
| 🎯 حالت پردازش | ${mode} |
| 📊 تعداد شیت‌ها | ${relatedSheets.length} |

---

## 📝 درخواست اصلی (پرامپت)

\`\`\`
${originalPrompt}
\`\`\`

---

`;
    
    // ========================================
    // 5. ایجاد Spreadsheet آرشیو و کپی شیت‌ها
    // ========================================
    const archiveSpreadsheet = SpreadsheetApp.create(folderName + '_Sheets');
    const archiveFile = DriveApp.getFileById(archiveSpreadsheet.getId());
    
    let continuationNumber = 0;
    let allResponses = [];
    let allScores = [];
    let judgeResult = null;
    
    relatedSheets.forEach((sheet, idx) => {
      try {
        const sheetName = sheet.getName();
        
        // کپی شیت به آرشیو
        sheet.copyTo(archiveSpreadsheet);
        Logger.log('  ✅ کپی شد: ' + sheetName);
        
        // ========================================
        // استخراج محتوای کامل برای Markdown
        // ========================================
        
        if (sheetName.includes('Full_')) {
          // ========================================
          // شیت پاسخ‌های کامل
          // ========================================
          fullMarkdown += `## 📄 پاسخ‌های کامل مدل‌ها\n\n`;
          fullMarkdown += `> این بخش شامل پاسخ‌های کامل و بدون خلاصه‌سازی هر مدل است.\n\n`;
          
          const data = sheet.getDataRange().getValues();
          for (let i = 1; i < data.length; i++) {
            if (data[i][0] && data[i][1]) {
              const round = data[i][0];
              const model = data[i][1];
              const response = data[i][2] || '';
              const tokens = data[i][3] || '';
              
              fullMarkdown += `### 🤖 دور ${round} - ${model}\n\n`;
              fullMarkdown += `**توکن‌ها:** ${tokens}\n\n`;
              fullMarkdown += `#### پاسخ کامل:\n\n`;
              fullMarkdown += `${response}\n\n`;  // پاسخ کامل بدون محدودیت
              fullMarkdown += `\n---\n\n`;
              
              allResponses.push({ round, model, response, tokens });
            }
          }
          
        } else if (sheetName.includes('Work_') || sheetName.includes('Done_')) {
          // ========================================
          // شیت اصلی Work/Done
          // ========================================
          
          // خواندن اطلاعات مدل‌ها و نقش‌ها
          fullMarkdown += `## 🎭 مدل‌ها و نقش‌های تخصیص داده شده\n\n`;
          fullMarkdown += `| # | مدل | نقش | وضعیت |\n`;
          fullMarkdown += `|---|-----|-----|-------|\n`;
          
          for (let row = 7; row <= 13; row++) {
            const num = sheet.getRange(`A${row}`).getValue();
            const model = sheet.getRange(`B${row}`).getValue();
            const role = sheet.getRange(`C${row}`).getValue();
            const status = sheet.getRange(`H${row}`).getValue();
            
            if (model && model !== '') {
              fullMarkdown += `| ${num} | ${model} | ${role || '-'} | ${status || '-'} |\n`;
            }
          }
          fullMarkdown += `\n---\n\n`;
          
          // خواندن مراحل پردازش
          fullMarkdown += `## 📊 مراحل پردازش\n\n`;
          fullMarkdown += `| # | مرحله | وضعیت | شروع | پایان | نتیجه |\n`;
          fullMarkdown += `|---|-------|-------|------|-------|-------|\n`;
          
          for (let row = 18; row <= 28; row++) {
            const num = sheet.getRange(`A${row}`).getValue();
            const phase = sheet.getRange(`B${row}`).getValue();
            const status = sheet.getRange(`D${row}`).getValue();
            const start = sheet.getRange(`E${row}`).getValue();
            const end = sheet.getRange(`F${row}`).getValue();
            const result = sheet.getRange(`G${row}`).getValue();
            
            if (phase && phase !== '') {
              fullMarkdown += `| ${num} | ${phase} | ${status || '-'} | ${start || '-'} | ${end || '-'} | ${(result || '-').toString().substring(0, 50)} |\n`;
            }
          }
          fullMarkdown += `\n---\n\n`;
          
          // خواندن پاسخ‌ها از جدول پاسخ‌ها (ردیف 34+)
          fullMarkdown += `## 💬 پاسخ‌های دورهای مناظره\n\n`;
          
          let currentRound = 0;
          for (let row = 34; row <= 150; row++) {
            const roundNum = sheet.getRange(`A${row}`).getValue();
            const model = sheet.getRange(`B${row}`).getValue();
            const role = sheet.getRange(`C${row}`).getValue();
            const response = sheet.getRange(`D${row}`).getValue();
            const length = sheet.getRange(`E${row}`).getValue();
            const tokens = sheet.getRange(`F${row}`).getValue();
            const time = sheet.getRange(`G${row}`).getValue();
            const status = sheet.getRange(`H${row}`).getValue();
            
            if (!model || model === '') break;
            
            // هدر دور جدید
            if (roundNum && roundNum !== currentRound) {
              currentRound = roundNum;
              fullMarkdown += `\n### 🔄 دور ${roundNum}\n\n`;
            }
            
            if (model && response) {
              fullMarkdown += `#### 🤖 ${model}`;
              if (role) fullMarkdown += ` (${role})`;
              fullMarkdown += `\n\n`;
              
              fullMarkdown += `- **طول پاسخ:** ${length || response.length} کاراکتر\n`;
              fullMarkdown += `- **توکن‌ها:** ${tokens || '-'}\n`;
              fullMarkdown += `- **زمان:** ${time || '-'}\n`;
              fullMarkdown += `- **وضعیت:** ${status || '-'}\n\n`;
              
              fullMarkdown += `**پاسخ کامل:**\n\n`;
              fullMarkdown += `${response}\n\n`;  // پاسخ کامل بدون محدودیت
              fullMarkdown += `---\n\n`;
            }
          }
          
          // خواندن امتیازات (اگر وجود داشته باشد)
          try {
            const scoresSheet = ss.getSheetByName('امتیازات');
            if (scoresSheet) {
              const scoresData = scoresSheet.getDataRange().getValues();
              fullMarkdown += `## ⭐ امتیازات\n\n`;
              fullMarkdown += `| امتیازدهنده | هدف | امتیاز | توضیحات |\n`;
              fullMarkdown += `|------------|-----|-------|----------|\n`;
              
              for (let i = 1; i < scoresData.length; i++) {
                if (scoresData[i][0] && scoresData[i][0].toString().includes(idPart.substring(0, 8))) {
                  fullMarkdown += `| ${scoresData[i][1] || '-'} | ${scoresData[i][2] || '-'} | ${scoresData[i][3] || '-'} | ${(scoresData[i][4] || '-').toString().substring(0, 100)} |\n`;
                }
              }
              fullMarkdown += `\n---\n\n`;
            }
          } catch (e) {}
          
          // خواندن داوری (اگر وجود داشته باشد)
          try {
            const judgeSheet = ss.getSheetByName('داوری');
            if (judgeSheet) {
              const judgeData = judgeSheet.getDataRange().getValues();
              for (let i = 1; i < judgeData.length; i++) {
                if (judgeData[i][0] && judgeData[i][0].toString().includes(idPart.substring(0, 8))) {
                  fullMarkdown += `## ⚖️ داوری نهایی\n\n`;
                  fullMarkdown += `**داور:** ${judgeData[i][1] || '-'}\n\n`;
                  fullMarkdown += `**برنده:** ${judgeData[i][2] || '-'}\n\n`;
                  fullMarkdown += `**دلیل:**\n\n${judgeData[i][3] || '-'}\n\n`;
                  fullMarkdown += `---\n\n`;
                  break;
                }
              }
            }
          } catch (e) {}
          
        } else if (sheetName.includes('CONT-') || sheetName.includes('ادامه')) {
          // ========================================
          // شیت‌های ادامه پردازش
          // ========================================
          continuationNumber++;
          fullMarkdown += `## 🔄 ادامه پردازش #${continuationNumber}\n\n`;
          
          // سوال جدید
          const contQuestion = sheet.getRange('B3').getValue() || sheet.getRange('B2').getValue();
          fullMarkdown += `### ❓ سوال/ابهام جدید:\n\n`;
          fullMarkdown += `\`\`\`\n${contQuestion}\n\`\`\`\n\n`;
          
          // پاسخ‌های ادامه
          fullMarkdown += `### 💬 پاسخ‌ها:\n\n`;
          
          for (let row = 7; row <= 20; row++) {
            const model = sheet.getRange(`B${row}`).getValue();
            const response = sheet.getRange(`D${row}`).getValue();
            const status = sheet.getRange(`H${row}`).getValue();
            
            if (model && response) {
              fullMarkdown += `#### 🤖 ${model}\n\n`;
              fullMarkdown += `**وضعیت:** ${status || '-'}\n\n`;
              fullMarkdown += `**پاسخ کامل:**\n\n`;
              fullMarkdown += `${response}\n\n`;  // پاسخ کامل
              fullMarkdown += `---\n\n`;
            }
          }
        }
        
      } catch (e) {
        Logger.log('  ⚠️ خطا در کپی/استخراج: ' + sheet.getName() + ' - ' + e);
      }
    });
    
    // حذف شیت پیش‌فرض
    try {
      const defaultSheet = archiveSpreadsheet.getSheetByName('Sheet1');
      if (defaultSheet && archiveSpreadsheet.getSheets().length > 1) {
        archiveSpreadsheet.deleteSheet(defaultSheet);
      }
    } catch (e) {}
    
    // انتقال فایل آرشیو به فولدر پروژه
    archiveFile.moveTo(projectFolder);
    Logger.log('📄 آرشیو Spreadsheet منتقل شد');
    
    // ========================================
    // 6. استخراج و ذخیره کدها + اضافه کردن به Markdown
    // ========================================
    let extractedCodes = [];
    let codeCount = 0;
    
    try {
      const codesFolder = projectFolder.createFolder('کدهای_تولیدی');
      
      relatedSheets.forEach(sheet => {
        const data = sheet.getDataRange().getValues();
        data.forEach((row, rowIdx) => {
          row.forEach((cell, colIdx) => {
            if (typeof cell === 'string' && cell.includes('```')) {
              // استخراج بلوک‌های کد
              const codeBlocks = cell.match(/```(\w+)?\n?([\s\S]*?)```/g);
              if (codeBlocks) {
                codeBlocks.forEach((block, blockIdx) => {
                  const langMatch = block.match(/```(\w+)?/);
                  const lang = langMatch?.[1] || 'txt';
                  const code = block.replace(/```\w*\n?/, '').replace(/```$/, '').trim();
                  
                  if (code.length > 50) {
                    const ext = getCodeExtension(lang);
                    const fileName = `code_${sheet.getName().substring(0,10)}_${rowIdx}_${blockIdx}.${ext}`;
                    const codeBlob = Utilities.newBlob(code, 'text/plain', fileName);
                    codesFolder.createFile(codeBlob);
                    codeCount++;
                    
                    extractedCodes.push({
                      fileName: fileName,
                      language: lang,
                      lines: code.split('\n').length,
                      preview: code.substring(0, 200)
                    });
                  }
                });
              }
            }
          });
        });
      });
      
      Logger.log('💻 تعداد فایل‌های کد: ' + codeCount);
      
      // اگه کدی نبود، فولدر رو حذف کن
      if (codeCount === 0) {
        codesFolder.setTrashed(true);
      }
    } catch (e) {
      Logger.log('⚠️ خطا در استخراج کدها: ' + e);
    }
    
    // ========================================
    // 7. تکمیل فایل Markdown با کدها
    // ========================================
    if (extractedCodes.length > 0) {
      fullMarkdown += `\n## 💻 کدهای استخراج شده\n\n`;
      fullMarkdown += `> تعداد ${extractedCodes.length} فایل کد از پاسخ‌ها استخراج و ذخیره شد.\n\n`;
      fullMarkdown += `| # | نام فایل | زبان | تعداد خط |\n`;
      fullMarkdown += `|---|----------|------|----------|\n`;
      
      extractedCodes.forEach((code, idx) => {
        fullMarkdown += `| ${idx + 1} | \`${code.fileName}\` | ${code.language} | ${code.lines} |\n`;
      });
      
      fullMarkdown += `\n### پیش‌نمایش کدها:\n\n`;
      extractedCodes.forEach((code, idx) => {
        fullMarkdown += `#### ${idx + 1}. ${code.fileName}\n\n`;
        fullMarkdown += `\`\`\`${code.language}\n${code.preview}${code.preview.length >= 200 ? '\n// ... ادامه در فایل ...' : ''}\n\`\`\`\n\n`;
      });
    }
    
    // بخش پایانی
    fullMarkdown += `\n---\n\n`;
    fullMarkdown += `## 📊 خلاصه آماری\n\n`;
    fullMarkdown += `| عنوان | مقدار |\n`;
    fullMarkdown += `|-------|-------|\n`;
    fullMarkdown += `| تعداد شیت‌های آرشیو شده | ${relatedSheets.length} |\n`;
    fullMarkdown += `| تعداد ادامه‌ها | ${continuationNumber} |\n`;
    fullMarkdown += `| تعداد کدهای استخراج شده | ${extractedCodes.length} |\n`;
    fullMarkdown += `\n---\n\n`;
    fullMarkdown += `## 🔗 لینک‌های مرتبط\n\n`;
    fullMarkdown += `- 📁 [فولدر آرشیو](${projectFolder.getUrl()})\n`;
    fullMarkdown += `- 📊 [Spreadsheet آرشیو](${archiveSpreadsheet.getUrl()})\n`;
    fullMarkdown += `\n---\n\n`;
    fullMarkdown += `> 🤖 **تولید شده توسط سیستم AI Debate v12.0**\n>\n`;
    fullMarkdown += `> 📅 تاریخ آرشیو: ${new Date().toLocaleString('fa-IR')}\n>\n`;
    fullMarkdown += `> 🆔 شناسه پروژه: \`${promptId}\`\n`;
    
    const mdBlob = Utilities.newBlob(fullMarkdown, 'text/markdown', 'FULL_REPORT.md');
    projectFolder.createFile(mdBlob);
    Logger.log('📄 فایل Markdown کامل ایجاد شد: ' + fullMarkdown.length + ' کاراکتر');
    
    // ========================================
    // 8. آپدیت وضعیت در شیت آرشیو
    // ========================================
    const archiveListSheet = ss.getSheetByName('آرشیو');
    if (archiveListSheet) {
      archiveListSheet.appendRow([
        promptId,
        new Date().toLocaleString('fa-IR'),
        projectFolder.getUrl(),
        relatedSheets.length + ' شیت',
        mode,
        promptSummary.substring(0, 50)
      ]);
    }
    
    // ========================================
    // 9. حذف شیت‌ها از گوگل شیت اصلی
    // ========================================
    Logger.log('🗑️ حذف شیت‌های اصلی...');
    let deletedCount = 0;
    
    relatedSheets.forEach(sheet => {
      try {
        const sheetName = sheet.getName();
        ss.deleteSheet(sheet);
        deletedCount++;
        Logger.log('  ✅ حذف شد: ' + sheetName);
      } catch (e) {
        Logger.log('  ⚠️ خطا در حذف: ' + sheet.getName() + ' - ' + e);
      }
    });
    
    Logger.log('🗑️ ' + deletedCount + ' شیت حذف شد');
    
    // ========================================
    // 10. پاک کردن Cache
    // ========================================
    try {
      const cache = CacheService.getScriptCache();
      cache.remove('STATE_' + promptId);
      cache.remove('JOURNAL_' + promptId);
      Logger.log('🧹 Cache پاک شد');
    } catch (e) {}
    
    Logger.log('✅ پروژه با موفقیت آرشیو شد!');
    Logger.log('  📁 لینک فولدر: ' + projectFolder.getUrl());
    
    return {
      success: true,
      promptId: promptId,
      folderName: folderName,
      folderId: projectFolderId,
      folderUrl: projectFolder.getUrl(),
      archiveSpreadsheetUrl: archiveSpreadsheet.getUrl(),
      sheetsArchived: relatedSheets.length,
      sheetsDeleted: deletedCount
    };
    
  } catch (error) {
    Logger.log('❌ خطا در بستن پروژه: ' + error);
    Logger.log('  Stack: ' + error.stack);
    return { success: false, error: error.message };
  }
}

/**
 * دریافت پسوند فایل از زبان
 */
function getCodeExtension(lang) {
  const extensions = {
    'javascript': 'js', 'js': 'js', 'typescript': 'ts', 'ts': 'ts',
    'python': 'py', 'py': 'py', 'java': 'java', 'cpp': 'cpp', 'c': 'c',
    'csharp': 'cs', 'cs': 'cs', 'html': 'html', 'css': 'css',
    'json': 'json', 'xml': 'xml', 'sql': 'sql', 'bash': 'sh', 'sh': 'sh',
    'mq5': 'mq5', 'mql5': 'mq5', 'mq4': 'mq4', 'gs': 'gs', 'gas': 'gs'
  };
  return extensions[lang?.toLowerCase()] || 'txt';
}

/**
 * تولید نام مناسب برای فولدر از متن پرامپت
 */
function generateFolderName(prompt) {
  // حذف کاراکترهای خاص و محدود کردن طول
  let name = prompt
    .replace(/[\\/:*?"<>|]/g, '')
    .replace(/\s+/g, '_')
    .substring(0, 50)
    .trim();
  
  // اگر خیلی کوتاه شد
  if (name.length < 5) {
    name = 'پروژه_' + Date.now().toString(36);
  }
  
  return name;
}

/**
 * جمع‌آوری فایل‌های آپلود شده
 */
function collectUploadedFiles(promptId, ss) {
  const fileIds = [];
  
  try {
    // از شیت پرامپت‌ها
    const promptSheet = ss.getSheetByName('پرامپت‌ها');
    if (promptSheet) {
      const data = promptSheet.getDataRange().getValues();
      for (let i = 1; i < data.length; i++) {
        if (data[i][0] === promptId || (data[i][0] && data[i][0].includes(promptId.substring(0, 8)))) {
          // ستون attachments
          const attachments = data[i][8] || data[i][9];
          if (attachments) {
            try {
              const parsed = JSON.parse(attachments);
              if (Array.isArray(parsed)) {
                parsed.forEach(att => {
                  if (att.id) fileIds.push(att.id);
                  if (att.fileId) fileIds.push(att.fileId);
                });
              }
            } catch (e) {}
          }
        }
      }
    }
    
    // از Work Sheet
    const workSheet = findWorkSheet(promptId);
    if (workSheet) {
      // ستون فایل‌ها (معمولاً G یا H)
      const attachmentCell = workSheet.getRange('G2').getValue();
      if (attachmentCell) {
        try {
          const parsed = JSON.parse(attachmentCell);
          if (Array.isArray(parsed)) {
            parsed.forEach(att => {
              if (att.id) fileIds.push(att.id);
              if (att.fileId) fileIds.push(att.fileId);
            });
          }
        } catch (e) {}
      }
    }
  } catch (e) {
    Logger.log('⚠️ خطا در جمع‌آوری فایل‌های آپلود: ' + e);
  }
  
  return [...new Set(fileIds)]; // حذف تکراری‌ها
}

/**
 * جمع‌آوری فایل‌های تولید شده توسط AI
 */
function collectGeneratedFiles(promptId, ss) {
  const fileIds = [];
  
  try {
    // از شیت آرشیو
    const archiveSheet = ss.getSheetByName('آرشیو');
    if (archiveSheet) {
      const data = archiveSheet.getDataRange().getValues();
      for (let i = 1; i < data.length; i++) {
        if (data[i][0] === promptId || (data[i][0] && data[i][0].includes(promptId.substring(0, 8)))) {
          // لینک‌های Doc یا Drive
          for (let j = 0; j < data[i].length; j++) {
            const cell = data[i][j];
            if (typeof cell === 'string') {
              // استخراج ID از لینک‌های Drive
              const matches = cell.match(/\/d\/([a-zA-Z0-9_-]+)/g);
              if (matches) {
                matches.forEach(m => {
                  const id = m.replace('/d/', '');
                  if (id.length > 10) fileIds.push(id);
                });
              }
            }
          }
        }
      }
    }
    
    // از فولدر پیش‌فرض
    try {
      const folder = DriveApp.getFolderById(CONFIG.folderId);
      const files = folder.getFilesByName(promptId.substring(0, 8));
      while (files.hasNext()) {
        fileIds.push(files.next().getId());
      }
    } catch (e) {}
    
  } catch (e) {
    Logger.log('⚠️ خطا در جمع‌آوری فایل‌های تولیدی: ' + e);
  }
  
  return [...new Set(fileIds)];
}

/**
 * ایجاد فایل README برای پروژه
 */
function createProjectReadme(promptId, prompt, mode, startTime, sheetsCount, uploadedCount, generatedCount) {
  const now = new Date().toLocaleString('fa-IR');
  
  return `
========================================
📦 آرشیو پروژه AI Debate System
========================================

🆔 شناسه پروژه: ${promptId}
📅 تاریخ شروع: ${startTime}
📅 تاریخ آرشیو: ${now}

----------------------------------------
📝 درخواست اصلی:
----------------------------------------
${prompt.substring(0, 2000)}
${prompt.length > 2000 ? '\n... (ادامه در فایل اصلی)' : ''}

----------------------------------------
⚙️ تنظیمات:
----------------------------------------
🎯 حالت پردازش: ${mode}
📋 تعداد شیت‌ها: ${sheetsCount}
📎 فایل‌های آپلود شده: ${uploadedCount}
🤖 فایل‌های تولیدی: ${generatedCount}

----------------------------------------
📁 محتویات فولدر:
----------------------------------------
- ${promptId}_Archive.xlsx : آرشیو کامل شیت‌ها
- فایل‌های_آپلود_شده/ : فایل‌های اصلی کاربر
- فایل‌های_تولیدی/ : خروجی‌های AI
- README.txt : این فایل

========================================
🔗 AI Debate & Collaboration System
   Powered by GPT-4, Claude, Gemini, DeepSeek
========================================
`;
}

/**
 * دریافت وضعیت پروژه
 */
function getProjectStatus(promptId) {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.sheetId);
    const workSheet = findWorkSheet(promptId);
    
    if (!workSheet) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    // شمارش ادامه‌ها
    let continuations = 0;
    const sheets = ss.getSheets();
    const shortId = promptId.substring(0, 8);
    
    sheets.forEach(sheet => {
      if (sheet.getName().startsWith('CONT-' + shortId)) {
        continuations++;
      }
    });
    
    // وضعیت
    const status = workSheet.getRange('H1').getValue();
    const originalPrompt = workSheet.getRange('B1').getValue();
    
    return {
      success: true,
      promptId: promptId,
      status: status,
      prompt: originalPrompt.substring(0, 200),
      continuations: continuations,
      isArchived: workSheet.getName().startsWith('[آرشیو]'),
      workSheetName: workSheet.getName()
    };
    
  } catch (error) {
    return { success: false, error: error.message };
  }
}


// ╔═══════════════════════════════════════════════════════════════════════════════╗
// ║                                                                               ║
// ║   🚀 PERSISTENT PROJECT MANAGEMENT SYSTEM v1.0                               ║
// ║   سیستم مدیریت پروژه پایدار با قابلیت‌های پیشرفته                              ║
// ║                                                                               ║
// ╚═══════════════════════════════════════════════════════════════════════════════╝

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 PERSISTENT PROJECT: CONSTANTS & CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

const PERSISTENT_PROJECT_CONFIG = {
  // فولدر اصلی پروژه‌ها
  ROOT_FOLDER_ID: '1QJa3IkiKtKHZ9Hu3GIZIMo8WblncO_U6',
  
  // ساختار فولدری
  FOLDER_STRUCTURE: {
    UPLOADS: '01_Uploads',
    GENERATED: '02_Generated',
    GENERATED_CODE: '02_Generated/Code',
    GENERATED_DOCS: '02_Generated/Documents',
    GENERATED_IMAGES: '02_Generated/Images',
    VERSIONS: '03_Versions',
    LOGS: '04_Logs',
    TESTS: '05_Tests'
  },
  
  // فایل‌های اصلی
  MASTER_FILES: {
    PROJECT_SHEET: 'Project_Master',
    FLOWCHART: 'Flowchart.html',
    CONTEXT: 'Context.json'
  },
  
  // شیت‌های Project_Master
  SHEETS: {
    DASHBOARD: 'Dashboard',
    CONVERSATIONS: 'Conversations',
    FILES_REGISTRY: 'Files Registry',
    MODELS_PERFORMANCE: 'Models Performance',
    PROJECT_TREE: 'Project Tree',
    PHASES: 'Phases',
    TIMELINE: 'Timeline',
    METRICS: 'Metrics'
  },
  
  // ✅ v16.0: وضعیت‌های فاز با رنگ‌بندی هوشمند - PHASE 3
  PHASE_STATUS: {
    PENDING: { code: 'pending', color: '#9E9E9E', label: '⏳ در انتظار', icon: '⏳', priority: 0 },
    IN_PROGRESS: { code: 'in_progress', color: '#2196F3', label: '🔄 در حال انجام', icon: '🔄', priority: 1, animate: true },
    COMPLETED: { code: 'completed', color: '#4CAF50', label: '✅ تکمیل شده', icon: '✅', priority: 2 },
    FAILED: { code: 'failed', color: '#F44336', label: '❌ ناموفق', icon: '❌', priority: -1 },
    PAUSED: { code: 'paused', color: '#FF9800', label: '⏸️ متوقف', icon: '⏸️', priority: 0.5 },
    ROLLBACK: { code: 'rollback', color: '#9C27B0', label: '↩️ برگشت', icon: '↩️', priority: -0.5 },
    SKIPPED: { code: 'skipped', color: '#607D8B', label: '⏭️ رد شده', icon: '⏭️', priority: 2 }
  },
  
  // ✅ v16.0: تنظیمات نمودار درختی
  TREE_DIAGRAM: {
    DEFAULT_LAYOUT: 'vertical',  // vertical | horizontal
    SHOW_TOOLTIPS: true,
    SHOW_PROGRESS_BARS: true,
    ANIMATION_ENABLED: true,
    AUTO_SCROLL_TO_CURRENT: true,
    COLORS: {
      CONNECTION_LINE: '#E0E0E0',
      CONNECTION_LINE_COMPLETED: '#4CAF50',
      CURRENT_INDICATOR: '#9C27B0'
    }
  },
  
  // انواع پروژه
  PROJECT_TYPES: {
    CODING: { id: 'coding', label: '💻 کدنویسی', icon: '💻' },
    LEARNING: { id: 'learning', label: '📚 آموزش', icon: '📚' },
    RESEARCH: { id: 'research', label: '🔬 تحقیق', icon: '🔬' },
    WRITING: { id: 'writing', label: '✍️ نگارش', icon: '✍️' },
    DESIGN: { id: 'design', label: '🎨 طراحی', icon: '🎨' },
    ANALYSIS: { id: 'analysis', label: '📊 تحلیل', icon: '📊' },
    CUSTOM: { id: 'custom', label: '🔧 سفارشی', icon: '🔧' }
  },
  
  // سطوح پیچیدگی
  COMPLEXITY_LEVELS: {
    BEGINNER: { level: 1, label: 'مبتدی', multiplier: 1.0 },
    INTERMEDIATE: { level: 2, label: 'متوسط', multiplier: 1.5 },
    ADVANCED: { level: 3, label: 'پیشرفته', multiplier: 2.0 },
    EXPERT: { level: 4, label: 'حرفه‌ای', multiplier: 3.0 }
  },
  
  // ✅ v16.0: تنظیمات آرشیو - پروژه‌ها هرگز خودکار آرشیو نمی‌شوند
  ARCHIVE_SETTINGS: {
    AUTO_ARCHIVE: false,  // 🔥 غیرفعال: پروژه‌ها هرگز خودکار آرشیو نمی‌شوند
    MANUAL_ARCHIVE_ONLY: true,  // فقط آرشیو دستی
    ARCHIVE_CONFIRM_STEPS: 2,  // تأیید ۲ مرحله‌ای
    KEEP_FILES_ON_DELETE: true  // حفظ فایل‌ها در Drive هنگام حذف پروژه
  },
  
  // ✅ v16.0: تنظیمات ذخیره وضعیت
  STATE_PERSISTENCE: {
    AUTO_SAVE: true,
    SAVE_INTERVAL_MS: 30000,  // هر ۳۰ ثانیه
    KEEP_HISTORY: true,
    MAX_HISTORY_ENTRIES: 100,
    RESUME_ON_LOAD: true  // بازگشت به مرحله قبلی پس از بستن برنامه
  }
};

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 PERSISTENT PROJECT: MODEL SCORING SYSTEM
// ═══════════════════════════════════════════════════════════════════════════════

const MODEL_SCORING_SYSTEM = {
  CRITERIA: {
    ACCURACY: { weight: 0.30, label: 'دقت پاسخ', icon: '🎯' },
    COMPLETENESS: { weight: 0.25, label: 'کامل بودن', icon: '📋' },
    SPEED: { weight: 0.15, label: 'سرعت', icon: '⚡' },
    RELEVANCE: { weight: 0.20, label: 'مرتبط بودن', icon: '🔗' },
    CREATIVITY: { weight: 0.10, label: 'خلاقیت', icon: '💡' }
  },
  
  // ✅ v16.0: آستانه‌های عملکرد با اقدامات خودکار
  THRESHOLDS: {
    EXCELLENT: { min: 90, label: 'عالی', color: '#4CAF50', action: 'keep' },
    GOOD: { min: 75, label: 'خوب', color: '#8BC34A', action: 'keep' },
    ACCEPTABLE: { min: 60, label: 'قابل قبول', color: '#FFC107', action: 'monitor' },
    POOR: { min: 40, label: 'ضعیف', color: '#FF9800', action: 'warn' },
    REPLACE: { min: 0, label: 'نیاز به جایگزینی', color: '#F44336', action: 'replace' }
  },
  
  // ✅ v16.0: تنظیمات جایگزینی خودکار
  AUTO_REPLACEMENT: {
    ENABLED: true,
    MIN_SAMPLES: 5,  // حداقل نمونه برای تصمیم‌گیری
    DROP_THRESHOLD: 15,  // درصد کاهش برای پیشنهاد جایگزینی
    SUGGEST_ONLY: true,  // فقط پیشنهاد بده، خودکار جایگزین نکن
    NOTIFY_USER: true  // اطلاع‌رسانی به کاربر
  },
  
  MODEL_CAPABILITIES: {
    'gpt-4-turbo': { coding: 95, learning: 90, research: 92, writing: 88, design: 70, analysis: 90 },
    'gpt-4o': { coding: 90, learning: 88, research: 88, writing: 85, design: 85, analysis: 88 },
    'claude-sonnet-4-20250514': { coding: 92, learning: 95, research: 90, writing: 95, design: 75, analysis: 92 },
    'claude-3-5-sonnet-20241022': { coding: 90, learning: 93, research: 88, writing: 93, design: 72, analysis: 90 },
    'gemini-2.5-pro': { coding: 85, learning: 88, research: 90, writing: 82, design: 80, analysis: 88 },
    'gemini-2.0-flash': { coding: 82, learning: 85, research: 85, writing: 80, design: 78, analysis: 85 },
    'deepseek-chat': { coding: 88, learning: 80, research: 82, writing: 75, design: 60, analysis: 85 },
    'deepseek-coder': { coding: 95, learning: 70, research: 75, writing: 65, design: 50, analysis: 80 }
  }
};

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 PERSISTENT PROJECT: CONTEXT STRUCTURE
// ═══════════════════════════════════════════════════════════════════════════════

function getEmptyProjectContext() {
  return {
    project: {
      id: '', name: '', type: '', description: '', goal: '',
      createdAt: '', updatedAt: '', status: 'active',
      complexity: 'intermediate', language: 'fa'
    },
    phases: [],
    currentPhase: { id: '', name: '', step: 0, totalSteps: 0, status: 'pending' },
    conversations: [],
    models: { active: [], history: [], scores: {} },
    files: { uploaded: [], generated: [], versions: {} },
    tree: { nodes: [], edges: [], lastUpdate: '' },
    metrics: { totalConversations: 0, totalFiles: 0, totalVersions: 0, averageModelScore: 0, successRate: 0 },
    codeSync: {
      backend: { lastCode: '', version: 0, lastUpdate: '' },
      frontend: { lastCode: '', version: 0, lastUpdate: '' }
    },
    summary: { shortSummary: '', detailedSummary: '', keyDecisions: [], currentChallenges: [], nextSteps: [] }
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 PERSISTENT PROJECT: PROJECT CREATION
// ═══════════════════════════════════════════════════════════════════════════════

function createPersistentProject(config) {
  try {
    Logger.log('🚀 شروع ایجاد پروژه پایدار: ' + config.name);
    
    const projectId = 'proj_' + Date.now();
    const timestamp = new Date().toISOString().split('T')[0];
    const folderName = config.name.replace(/[^a-zA-Z0-9\u0600-\u06FF\s]/g, '_') + '_' + timestamp;
    
    // 1. ایجاد فولدر اصلی پروژه
    const rootFolder = DriveApp.getFolderById(PERSISTENT_PROJECT_CONFIG.ROOT_FOLDER_ID);
    const projectFolder = rootFolder.createFolder(folderName);
    const projectFolderId = projectFolder.getId();
    
    Logger.log('📁 فولدر پروژه ایجاد شد: ' + projectFolderId);
    
    // 2. ایجاد ساختار فولدری
    const folders = {};
    folders.uploads = projectFolder.createFolder(PERSISTENT_PROJECT_CONFIG.FOLDER_STRUCTURE.UPLOADS);
    folders.generated = projectFolder.createFolder('02_Generated');
    folders.versions = projectFolder.createFolder(PERSISTENT_PROJECT_CONFIG.FOLDER_STRUCTURE.VERSIONS);
    folders.logs = projectFolder.createFolder(PERSISTENT_PROJECT_CONFIG.FOLDER_STRUCTURE.LOGS);
    folders.tests = projectFolder.createFolder(PERSISTENT_PROJECT_CONFIG.FOLDER_STRUCTURE.TESTS);
    folders.code = folders.generated.createFolder('Code');
    folders.docs = folders.generated.createFolder('Documents');
    folders.images = folders.generated.createFolder('Images');
    folders.v1 = folders.versions.createFolder('v1');
    
    Logger.log('📂 ساختار فولدری ایجاد شد');
    
    // 3. ایجاد Spreadsheet اصلی
    const masterSheet = SpreadsheetApp.create(PERSISTENT_PROJECT_CONFIG.MASTER_FILES.PROJECT_SHEET);
    const masterSheetFile = DriveApp.getFileById(masterSheet.getId());
    masterSheetFile.moveTo(projectFolder);
    
    // 4. ایجاد شیت‌ها
    setupPersistentProjectSheets(masterSheet, config, projectId);
    
    Logger.log('📊 Spreadsheet اصلی ایجاد شد');
    
    // 5. ایجاد Context.json
    const context = getEmptyProjectContext();
    context.project = {
      id: projectId, name: config.name, type: config.type || 'custom',
      description: config.description || '', goal: config.goal || '',
      createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
      status: 'active', complexity: config.complexity || 'intermediate',
      language: config.language || 'fa'
    };
    context.phases = generateInitialPhases(config.type, config.customPhases);
    context.currentPhase = {
      id: context.phases[0]?.id || 'phase_1',
      name: context.phases[0]?.name || 'شروع',
      step: 0, totalSteps: context.phases[0]?.steps?.length || 1,
      status: 'in_progress'
    };
    context.models.active = config.models || ['gpt-4-turbo', 'claude-sonnet-4-20250514'];
    
    const contextFile = projectFolder.createFile(
      PERSISTENT_PROJECT_CONFIG.MASTER_FILES.CONTEXT,
      JSON.stringify(context, null, 2),
      'application/json'
    );
    
    Logger.log('📄 Context.json ایجاد شد');
    
    // 6. ایجاد Flowchart.html
    const flowchartHtml = generateFlowchartHtml(context, projectId);
    const flowchartFile = projectFolder.createFile(
      PERSISTENT_PROJECT_CONFIG.MASTER_FILES.FLOWCHART,
      flowchartHtml,
      'text/html'
    );
    
    Logger.log('🌳 Flowchart ایجاد شد');
    
    // 7. ذخیره در Properties
    const projectRegistry = getPersistentProjectRegistry();
    projectRegistry[projectId] = {
      id: projectId, name: config.name, type: config.type,
      folderId: projectFolderId, sheetId: masterSheet.getId(),
      contextFileId: contextFile.getId(), flowchartFileId: flowchartFile.getId(),
      createdAt: new Date().toISOString(), lastAccess: new Date().toISOString(),
      status: 'active'
    };
    savePersistentProjectRegistry(projectRegistry);
    
    Logger.log('✅ پروژه با موفقیت ایجاد شد: ' + projectId);
    
    return {
      success: true, projectId: projectId, folderId: projectFolderId,
      folderUrl: projectFolder.getUrl(), sheetId: masterSheet.getId(),
      sheetUrl: masterSheet.getUrl(), message: 'پروژه با موفقیت ایجاد شد'
    };
    
  } catch (error) {
    Logger.log('❌ خطا در ایجاد پروژه: ' + error.message);
    return { success: false, error: error.message };
  }
}

function setupPersistentProjectSheets(spreadsheet, config, projectId) {
  const sheets = PERSISTENT_PROJECT_CONFIG.SHEETS;
  const defaultSheet = spreadsheet.getSheetByName('Sheet1');
  
  // 1. Dashboard
  const dashboard = spreadsheet.insertSheet(sheets.DASHBOARD);
  dashboard.getRange('A1:H1').merge()
    .setValue('🎯 داشبورد پروژه: ' + config.name)
    .setFontSize(18).setFontWeight('bold')
    .setBackground('#1976D2').setFontColor('white').setHorizontalAlignment('center');
  
  const infoData = [
    ['شناسه پروژه:', projectId, '', 'نوع پروژه:', config.type || 'custom'],
    ['تاریخ ایجاد:', new Date().toLocaleDateString('fa-IR'), '', 'پیچیدگی:', config.complexity || 'intermediate'],
    ['وضعیت:', 'فعال ✅', '', 'زبان:', config.language || 'فارسی'],
    ['', '', '', '', ''],
    ['📊 آمار کلی', '', '', '', ''],
    ['تعداد مکالمات:', '0', '', 'تعداد فایل‌ها:', '0'],
    ['فاز فعلی:', '1', '', 'پیشرفت کل:', '0%'],
    ['میانگین امتیاز:', '-', '', 'آخرین به‌روزرسانی:', new Date().toLocaleString('fa-IR')]
  ];
  dashboard.getRange('A3:E10').setValues(infoData);
  dashboard.getRange('A3:A10').setFontWeight('bold').setBackground('#E3F2FD');
  dashboard.getRange('D3:D10').setFontWeight('bold').setBackground('#E3F2FD');
  dashboard.setColumnWidth(1, 150); dashboard.setColumnWidth(2, 200);
  dashboard.setColumnWidth(4, 150); dashboard.setColumnWidth(5, 200);
  
  // 2. Conversations
  const conversations = spreadsheet.insertSheet(sheets.CONVERSATIONS);
  conversations.getRange('A1:I1').setValues([['#', 'زمان', 'فاز', 'ورودی کاربر', 'مدل', 'پاسخ', 'امتیاز', 'مدت (ثانیه)', 'وضعیت']])
    .setFontWeight('bold').setBackground('#1976D2').setFontColor('white').setHorizontalAlignment('center');
  conversations.setColumnWidth(4, 400); conversations.setColumnWidth(6, 500);
  conversations.setFrozenRows(1);
  
  // 3. Files Registry
  const filesRegistry = spreadsheet.insertSheet(sheets.FILES_REGISTRY);
  filesRegistry.getRange('A1:J1').setValues([['#', 'نام فایل', 'نوع', 'مسیر', 'نسخه', 'حجم', 'تاریخ ایجاد', 'آخرین تغییر', 'لینک', 'توضیحات']])
    .setFontWeight('bold').setBackground('#4CAF50').setFontColor('white');
  filesRegistry.setFrozenRows(1);
  
  // 4. Models Performance
  const modelsPerf = spreadsheet.insertSheet(sheets.MODELS_PERFORMANCE);
  modelsPerf.getRange('A1:K1').setValues([['مدل', 'Provider', 'نوع پروژه', 'امتیاز دقت', 'امتیاز کامل بودن', 'امتیاز سرعت', 'امتیاز مرتبط بودن', 'امتیاز خلاقیت', 'میانگین کل', 'تعداد استفاده', 'آخرین استفاده']])
    .setFontWeight('bold').setBackground('#9C27B0').setFontColor('white');
  modelsPerf.setFrozenRows(1);
  
  // 5. Project Tree
  const projectTree = spreadsheet.insertSheet(sheets.PROJECT_TREE);
  projectTree.getRange('A1:J1').setValues([['Node ID', 'نام', 'نوع', 'Parent', 'وضعیت', 'رنگ', 'توضیحات', 'فایل‌های مرتبط', 'تاریخ شروع', 'تاریخ پایان']])
    .setFontWeight('bold').setBackground('#FF5722').setFontColor('white');
  projectTree.setFrozenRows(1);
  
  // 6. Phases
  const phases = spreadsheet.insertSheet(sheets.PHASES);
  phases.getRange('A1:I1').setValues([['فاز', 'نام', 'توضیحات', 'وضعیت', 'پیشرفت %', 'تاریخ شروع', 'تاریخ پایان', 'مدل‌ها', 'فایل‌های خروجی']])
    .setFontWeight('bold').setBackground('#673AB7').setFontColor('white');
  const phasesData = generateInitialPhases(config.type).map((p, i) => [
    i + 1, p.name, p.description || '', i === 0 ? 'در حال انجام' : 'در انتظار',
    i === 0 ? '0%' : '-', i === 0 ? new Date().toLocaleDateString('fa-IR') : '-', '-', '', ''
  ]);
  if (phasesData.length > 0) phases.getRange(2, 1, phasesData.length, 9).setValues(phasesData);
  phases.setFrozenRows(1);
  
  // 7. Timeline
  const timeline = spreadsheet.insertSheet(sheets.TIMELINE);
  timeline.getRange('A1:F1').setValues([['زمان', 'رویداد', 'نوع', 'فاز', 'جزئیات', 'کاربر/مدل']])
    .setFontWeight('bold').setBackground('#00BCD4').setFontColor('white');
  timeline.getRange('A2:F2').setValues([[new Date().toLocaleString('fa-IR'), 'ایجاد پروژه', 'system', '0', 'پروژه جدید ایجاد شد', 'System']]);
  timeline.setFrozenRows(1);
  
  // 8. Metrics
  const metrics = spreadsheet.insertSheet(sheets.METRICS);
  metrics.getRange('A1:D1').merge()
    .setValue('📊 آمار و متریک‌های پروژه')
    .setFontSize(16).setFontWeight('bold').setBackground('#607D8B').setFontColor('white');
  const metricsData = [
    ['متریک', 'مقدار', 'واحد', 'آخرین به‌روزرسانی'],
    ['تعداد کل مکالمات', '0', 'عدد', new Date().toLocaleString('fa-IR')],
    ['تعداد فایل‌های آپلود شده', '0', 'عدد', ''],
    ['تعداد فایل‌های تولید شده', '0', 'عدد', ''],
    ['میانگین امتیاز مدل‌ها', '0', 'درصد', ''],
    ['نرخ موفقیت', '0', 'درصد', '']
  ];
  metrics.getRange('A3:D8').setValues(metricsData);
  
  if (defaultSheet) spreadsheet.deleteSheet(defaultSheet);
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 PERSISTENT PROJECT: PHASE GENERATION
// ═══════════════════════════════════════════════════════════════════════════════

function generateInitialPhases(projectType, customPhases) {
  if (customPhases && customPhases.length > 0) {
    return customPhases.map((p, i) => ({
      id: 'phase_' + (i + 1), name: p.name, description: p.description || '',
      status: i === 0 ? 'in_progress' : 'pending', steps: p.steps || [], progress: 0
    }));
  }
  
  const phaseTemplates = {
    coding: [
      { name: '📋 تحلیل نیازمندی‌ها', description: 'درک و تحلیل دقیق نیازمندی‌های پروژه', steps: ['جمع‌آوری نیازمندی‌ها', 'تحلیل فنی', 'تعیین محدوده'] },
      { name: '🏗️ طراحی معماری', description: 'طراحی ساختار و معماری سیستم', steps: ['طراحی کلی', 'طراحی دیتابیس', 'طراحی API'] },
      { name: '💻 پیاده‌سازی', description: 'کدنویسی و توسعه', steps: ['Backend', 'Frontend', 'Integration'] },
      { name: '🧪 تست', description: 'تست و رفع اشکال', steps: ['Unit Tests', 'Integration Tests', 'Bug Fixes'] },
      { name: '🚀 استقرار', description: 'استقرار و راه‌اندازی', steps: ['Deployment', 'Configuration', 'Monitoring'] },
      { name: '📖 مستندسازی', description: 'تهیه مستندات', steps: ['Technical Docs', 'User Guide', 'API Docs'] }
    ],
    learning: [
      { name: '🎯 تعیین اهداف', description: 'مشخص کردن اهداف یادگیری', steps: ['اهداف کلی', 'اهداف جزئی', 'معیارهای موفقیت'] },
      { name: '📚 مبانی', description: 'یادگیری مفاهیم پایه', steps: ['تعاریف', 'اصول اولیه', 'مثال‌های ساده'] },
      { name: '📈 متوسط', description: 'مباحث متوسط', steps: ['مفاهیم پیشرفته‌تر', 'تمرین‌ها', 'پروژه‌های کوچک'] },
      { name: '🔬 پیشرفته', description: 'مباحث پیشرفته', steps: ['موضوعات تخصصی', 'پروژه‌های عملی', 'تحقیق'] },
      { name: '🏆 تسلط', description: 'رسیدن به تسلط', steps: ['پروژه جامع', 'ارزیابی', 'گواهینامه'] }
    ],
    research: [
      { name: '❓ تعریف مسئله', description: 'تعریف دقیق مسئله تحقیق', steps: ['سوال تحقیق', 'فرضیه‌ها', 'محدوده'] },
      { name: '📖 مرور ادبیات', description: 'بررسی منابع موجود', steps: ['جستجو', 'مطالعه', 'خلاصه‌سازی'] },
      { name: '🔬 روش تحقیق', description: 'طراحی روش تحقیق', steps: ['انتخاب روش', 'ابزارها', 'نمونه‌گیری'] },
      { name: '📊 جمع‌آوری داده', description: 'جمع‌آوری داده‌ها', steps: ['جمع‌آوری', 'پیش‌پردازش', 'ذخیره‌سازی'] },
      { name: '📈 تحلیل', description: 'تحلیل داده‌ها', steps: ['تحلیل آماری', 'تفسیر', 'نتیجه‌گیری'] },
      { name: '📝 گزارش', description: 'نگارش گزارش', steps: ['نوشتن', 'ویرایش', 'انتشار'] }
    ],
    writing: [
      { name: '💡 ایده‌پردازی', description: 'تولید و انتخاب ایده', steps: ['طوفان فکری', 'انتخاب موضوع', 'تحقیق اولیه'] },
      { name: '📑 طرح‌ریزی', description: 'ساختاردهی محتوا', steps: ['outline', 'فصل‌بندی', 'منابع'] },
      { name: '✍️ نگارش', description: 'نوشتن پیش‌نویس', steps: ['پیش‌نویس اول', 'بازنویسی', 'تکمیل'] },
      { name: '🔍 ویرایش', description: 'ویرایش و بازبینی', steps: ['ویرایش محتوایی', 'ویرایش ادبی', 'نهایی‌سازی'] },
      { name: '📤 انتشار', description: 'آماده‌سازی برای انتشار', steps: ['فرمت‌بندی', 'بازبینی نهایی', 'انتشار'] }
    ],
    design: [
      { name: '🔍 تحقیق', description: 'تحقیق و الهام', steps: ['بررسی رقبا', 'ترندها', 'نیازسنجی'] },
      { name: '💡 ایده‌پردازی', description: 'تولید ایده‌ها', steps: ['اسکچ', 'مودبورد', 'انتخاب مسیر'] },
      { name: '🎨 طراحی', description: 'طراحی اصلی', steps: ['Wireframe', 'Mockup', 'Prototype'] },
      { name: '🔄 تکرار', description: 'بازخورد و اصلاح', steps: ['تست کاربر', 'اصلاحات', 'نهایی‌سازی'] },
      { name: '📦 تحویل', description: 'آماده‌سازی فایل‌ها', steps: ['Export', 'مستندات', 'تحویل'] }
    ],
    analysis: [
      { name: '🎯 تعریف هدف', description: 'مشخص کردن هدف تحلیل', steps: ['سوالات کلیدی', 'معیارها', 'محدوده'] },
      { name: '📥 جمع‌آوری داده', description: 'گردآوری داده‌ها', steps: ['منابع داده', 'استخراج', 'پاکسازی'] },
      { name: '🔬 پردازش', description: 'پردازش داده‌ها', steps: ['تبدیل', 'ادغام', 'آماده‌سازی'] },
      { name: '📊 تحلیل', description: 'انجام تحلیل', steps: ['تحلیل توصیفی', 'تحلیل استنباطی', 'مدل‌سازی'] },
      { name: '📈 گزارش', description: 'ارائه نتایج', steps: ['داشبورد', 'گزارش', 'توصیه‌ها'] }
    ],
    custom: [
      { name: '🚀 شروع', description: 'آغاز پروژه', steps: ['تعریف', 'برنامه‌ریزی'] },
      { name: '⚙️ اجرا', description: 'اجرای پروژه', steps: ['پیاده‌سازی', 'پیگیری'] },
      { name: '✅ پایان', description: 'اتمام پروژه', steps: ['بازبینی', 'تحویل'] }
    ]
  };
  
  const template = phaseTemplates[projectType] || phaseTemplates.custom;
  return template.map((p, i) => ({
    id: 'phase_' + (i + 1), name: p.name, description: p.description,
    status: i === 0 ? 'in_progress' : 'pending', steps: p.steps || [], progress: 0
  }));
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 PERSISTENT PROJECT: REGISTRY
// ═══════════════════════════════════════════════════════════════════════════════

function getPersistentProjectRegistry() {
  const props = PropertiesService.getScriptProperties();
  const registryStr = props.getProperty('PERSISTENT_PROJECTS_REGISTRY');
  return registryStr ? JSON.parse(registryStr) : {};
}

function savePersistentProjectRegistry(registry) {
  const props = PropertiesService.getScriptProperties();
  props.setProperty('PERSISTENT_PROJECTS_REGISTRY', JSON.stringify(registry));
}

function getPersistentProjects() {
  try {
    const registry = getPersistentProjectRegistry();
    const projects = Object.values(registry).map(p => {
      let folderExists = false, folderUrl = '';
      try {
        const folder = DriveApp.getFolderById(p.folderId);
        folderExists = true;
        folderUrl = folder.getUrl();
      } catch (e) { folderExists = false; }
      return { ...p, folderExists, folderUrl };
    });
    projects.sort((a, b) => new Date(b.lastAccess) - new Date(a.lastAccess));
    return { success: true, projects: projects, count: projects.length };
  } catch (error) {
    Logger.log('❌ خطا در دریافت پروژه‌ها: ' + error.message);
    return { success: false, error: error.message, projects: [] };
  }
}

function getPersistentModelProvider(modelId) {
  if (modelId.startsWith('gpt')) return 'OpenAI';
  if (modelId.startsWith('claude')) return 'Anthropic';
  if (modelId.startsWith('gemini')) return 'Google';
  if (modelId.startsWith('deepseek')) return 'DeepSeek';
  if (modelId.includes('/')) return 'OpenRouter';
  return 'Unknown';
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 PERSISTENT PROJECT: LOAD & RESUME
// ═══════════════════════════════════════════════════════════════════════════════

function loadPersistentProject(projectId) {
  try {
    Logger.log('📂 بارگذاری پروژه: ' + projectId);
    
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    
    if (!projectInfo) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    const spreadsheet = SpreadsheetApp.openById(projectInfo.sheetId);
    
    registry[projectId].lastAccess = new Date().toISOString();
    savePersistentProjectRegistry(registry);
    
    const folder = DriveApp.getFolderById(projectInfo.folderId);
    const folderStructure = getPersistentFolderStructure(folder);
    
    Logger.log('✅ پروژه بارگذاری شد');
    
    return {
      success: true, projectId: projectId, projectInfo: projectInfo,
      context: context, sheetUrl: spreadsheet.getUrl(), folderUrl: folder.getUrl(),
      folderStructure: folderStructure, currentPhase: context.currentPhase,
      models: context.models, metrics: context.metrics, summary: context.summary
    };
    
  } catch (error) {
    Logger.log('❌ خطا در بارگذاری پروژه: ' + error.message);
    return { success: false, error: error.message };
  }
}

function getPersistentFolderStructure(folder, depth = 0) {
  if (depth > 3) return [];
  const structure = [];
  
  const files = folder.getFiles();
  while (files.hasNext()) {
    const file = files.next();
    structure.push({
      type: 'file', name: file.getName(), id: file.getId(),
      url: file.getUrl(), mimeType: file.getMimeType(),
      size: file.getSize(), lastUpdated: file.getLastUpdated().toISOString()
    });
  }
  
  const subfolders = folder.getFolders();
  while (subfolders.hasNext()) {
    const subfolder = subfolders.next();
    structure.push({
      type: 'folder', name: subfolder.getName(), id: subfolder.getId(),
      url: subfolder.getUrl(), children: getPersistentFolderStructure(subfolder, depth + 1)
    });
  }
  
  return structure;
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 PERSISTENT PROJECT: CONVERSATION MANAGEMENT
// ═══════════════════════════════════════════════════════════════════════════════

function addPersistentProjectConversation(projectId, userInput, modelResponses) {
  try {
    Logger.log('💬 افزودن مکالمه به پروژه: ' + projectId);
    
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    if (!projectInfo) return { success: false, error: 'پروژه یافت نشد' };
    
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    const conversationId = 'conv_' + Date.now();
    const conversation = {
      id: conversationId, timestamp: new Date().toISOString(),
      phase: context.currentPhase.id, phaseName: context.currentPhase.name,
      userInput: userInput,
      responses: modelResponses.map(r => ({
        model: r.model, response: r.response,
        score: r.score || 0, duration: r.duration || 0, tokens: r.tokens || 0
      })),
      status: 'completed'
    };
    
    context.conversations.push(conversation);
    context.metrics.totalConversations++;
    context.project.updatedAt = new Date().toISOString();
    
    for (const response of modelResponses) {
      updatePersistentModelScore(context, response.model, response.score, context.project.type);
    }
    
    contextFile.setContent(JSON.stringify(context, null, 2));
    
    const spreadsheet = SpreadsheetApp.openById(projectInfo.sheetId);
    const convSheet = spreadsheet.getSheetByName(PERSISTENT_PROJECT_CONFIG.SHEETS.CONVERSATIONS);
    
    for (const response of modelResponses) {
      convSheet.appendRow([
        context.conversations.length, new Date().toLocaleString('fa-IR'),
        context.currentPhase.name,
        userInput.substring(0, 500) + (userInput.length > 500 ? '...' : ''),
        response.model,
        response.response.substring(0, 1000) + (response.response.length > 1000 ? '...' : ''),
        response.score || '-', response.duration || '-', '✅'
      ]);
    }
    
    addPersistentTimelineEvent(spreadsheet, 'مکالمه جدید', 'conversation', 
      context.currentPhase.id, 'ورودی: ' + userInput.substring(0, 100), modelResponses[0]?.model || 'System');
    updatePersistentDashboard(spreadsheet, context);
    updatePersistentFlowchart(projectInfo, context);
    
    Logger.log('✅ مکالمه اضافه شد: ' + conversationId);
    
    return { success: true, conversationId: conversationId, totalConversations: context.metrics.totalConversations };
    
  } catch (error) {
    Logger.log('❌ خطا در افزودن مکالمه: ' + error.message);
    return { success: false, error: error.message };
  }
}

function updatePersistentModelScore(context, modelId, newScore, projectType) {
  if (!context.models.scores[modelId]) {
    context.models.scores[modelId] = { totalScore: 0, count: 0, average: 0, byType: {} };
  }
  
  const modelScore = context.models.scores[modelId];
  modelScore.totalScore += newScore;
  modelScore.count++;
  modelScore.average = Math.round(modelScore.totalScore / modelScore.count);
  
  if (!modelScore.byType[projectType]) {
    modelScore.byType[projectType] = { total: 0, count: 0, average: 0 };
  }
  modelScore.byType[projectType].total += newScore;
  modelScore.byType[projectType].count++;
  modelScore.byType[projectType].average = Math.round(
    modelScore.byType[projectType].total / modelScore.byType[projectType].count
  );
  
  if (modelScore.average < MODEL_SCORING_SYSTEM.THRESHOLDS.REPLACE) {
    context.models.needsReplacement = context.models.needsReplacement || [];
    if (!context.models.needsReplacement.includes(modelId)) {
      context.models.needsReplacement.push(modelId);
    }
  }
}

function addPersistentTimelineEvent(spreadsheet, event, type, phase, details, actor) {
  const timelineSheet = spreadsheet.getSheetByName(PERSISTENT_PROJECT_CONFIG.SHEETS.TIMELINE);
  timelineSheet.appendRow([new Date().toLocaleString('fa-IR'), event, type, phase, details, actor]);
}

function updatePersistentDashboard(spreadsheet, context) {
  const dashboard = spreadsheet.getSheetByName(PERSISTENT_PROJECT_CONFIG.SHEETS.DASHBOARD);
  dashboard.getRange('B6').setValue(context.metrics.totalConversations);
  dashboard.getRange('E6').setValue(context.metrics.totalFiles);
  dashboard.getRange('B7').setValue(context.currentPhase.id.replace('phase_', ''));
  
  const completedPhases = context.phases.filter(p => p.status === 'completed').length;
  const progress = Math.round((completedPhases / context.phases.length) * 100);
  dashboard.getRange('E7').setValue(progress + '%');
  
  const scores = Object.values(context.models.scores);
  if (scores.length > 0) {
    const avgScore = Math.round(scores.reduce((sum, s) => sum + s.average, 0) / scores.length);
    dashboard.getRange('B8').setValue(avgScore + '%');
  }
  dashboard.getRange('E8').setValue(new Date().toLocaleString('fa-IR'));
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 PERSISTENT PROJECT: SMART MODEL MANAGEMENT
// ═══════════════════════════════════════════════════════════════════════════════

function selectBestPersistentModel(projectId, taskDescription, complexity) {
  try {
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    const projectType = context.project.type;
    
    // فیلتر مدل‌های آرشیو شده
    const archivedDB = getArchivedModelsDB();
    const availableModels = (context.models.active || []).filter(modelId => {
      const archiveInfo = archivedDB.models[modelId];
      return !archiveInfo || !archiveInfo.archivedAt;
    });
    
    if (availableModels.length === 0) {
      // اگر همه مدل‌ها آرشیو شده‌اند، از مدل‌های پیش‌فرض استفاده کن
      const defaultModels = ['gpt-4-turbo', 'claude-sonnet-4-20250514', 'gemini-2.5-pro'];
      for (const m of defaultModels) {
        if (!archivedDB.models[m]?.archivedAt) {
          availableModels.push(m);
          break;
        }
      }
    }
    
    const modelScores = availableModels.map(modelId => {
      const baseScore = MODEL_SCORING_SYSTEM.MODEL_CAPABILITIES[modelId]?.[projectType] || 70;
      const historicalScore = context.models.scores[modelId]?.byType[projectType]?.average || baseScore;
      // کاهش امتیاز برای مدل‌های با خطا
      const errorPenalty = (archivedDB.models[modelId]?.errorCount || 0) * 5;
      const finalScore = Math.max(0, (baseScore * 0.4) + (historicalScore * 0.6) - errorPenalty);
      return { modelId, baseScore, historicalScore, finalScore, usageCount: context.models.scores[modelId]?.count || 0 };
    });
    
    modelScores.sort((a, b) => b.finalScore - a.finalScore);
    const bestModel = modelScores[0];
    
    if (!bestModel) {
      return { success: false, error: 'هیچ مدل فعالی یافت نشد' };
    }
    
    if (complexity === 'expert' && bestModel.finalScore < 85) {
      const strongerModels = ['gpt-4-turbo', 'claude-sonnet-4-20250514', 'gemini-2.5-pro'];
      const availableStronger = strongerModels.filter(m => 
        !availableModels.includes(m) && 
        hasPersistentApiKeyForModel(m) && 
        !archivedDB.models[m]?.archivedAt
      );
      if (availableStronger.length > 0) {
        return {
          success: true, selectedModel: bestModel.modelId, suggestUpgrade: true,
          suggestedModel: availableStronger[0], reason: 'پیچیدگی کار بالاست و مدل قوی‌تری پیشنهاد می‌شود',
          allScores: modelScores
        };
      }
    }
    
    return { success: true, selectedModel: bestModel.modelId, score: bestModel.finalScore, allScores: modelScores, suggestUpgrade: false };
    
  } catch (error) {
    Logger.log('❌ خطا در انتخاب مدل: ' + error.message);
    return { success: false, error: error.message };
  }
}

function replacePersistentWeakModel(projectId, oldModelId, newModelId, reason) {
  try {
    Logger.log('🔄 جایگزینی مدل: ' + oldModelId + ' → ' + newModelId);
    
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    context.models.active = context.models.active.filter(m => m !== oldModelId);
    context.models.history.push({
      modelId: oldModelId, replacedAt: new Date().toISOString(),
      replacedWith: newModelId, reason: reason,
      finalScore: context.models.scores[oldModelId]?.average || 0
    });
    
    if (!context.models.active.includes(newModelId)) {
      context.models.active.push(newModelId);
    }
    
    contextFile.setContent(JSON.stringify(context, null, 2));
    
    const spreadsheet = SpreadsheetApp.openById(projectInfo.sheetId);
    addPersistentTimelineEvent(spreadsheet, 'جایگزینی مدل', 'model_change', 
      context.currentPhase.id, `${oldModelId} → ${newModelId}: ${reason}`, 'System');
    
    Logger.log('✅ مدل جایگزین شد');
    
    return { success: true, oldModel: oldModelId, newModel: newModelId, activeModels: context.models.active };
    
  } catch (error) {
    Logger.log('❌ خطا در جایگزینی مدل: ' + error.message);
    return { success: false, error: error.message };
  }
}

function briefPersistentNewModel(projectId, modelId) {
  try {
    Logger.log('📋 توجیه مدل جدید: ' + modelId);
    
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    const briefing = generatePersistentProjectBriefing(context);
    
    const briefingPrompt = `
# 📋 توجیه پروژه

شما به پروژه‌ای با مشخصات زیر اضافه شده‌اید:

## اطلاعات پروژه
- **نام:** ${context.project.name}
- **نوع:** ${context.project.type}
- **هدف:** ${context.project.goal}
- **توضیحات:** ${context.project.description}
- **پیچیدگی:** ${context.project.complexity}

## وضعیت فعلی
- **فاز جاری:** ${context.currentPhase.name} (${context.currentPhase.id})
- **مرحله:** ${context.currentPhase.step} از ${context.currentPhase.totalSteps}
- **تعداد مکالمات:** ${context.conversations.length}

## خلاصه پیشرفت
${briefing.progressSummary}

## تصمیمات کلیدی
${briefing.keyDecisions.map((d, i) => `${i + 1}. ${d}`).join('\n')}

## چالش‌های فعلی
${briefing.currentChallenges.map((c, i) => `${i + 1}. ${c}`).join('\n')}

## فایل‌های مهم
${briefing.importantFiles.map(f => `- ${f.name}: ${f.description}`).join('\n')}

## آخرین مکالمات
${briefing.recentConversations.map((c, i) => `
### مکالمه ${i + 1}
**ورودی:** ${c.userInput.substring(0, 200)}...
**پاسخ:** ${c.response.substring(0, 300)}...
`).join('\n')}

---
لطفاً با در نظر گرفتن این اطلاعات، به کاربر کمک کنید.
`;
    
    return {
      success: true, briefingPrompt: briefingPrompt,
      context: { projectName: context.project.name, currentPhase: context.currentPhase, totalConversations: context.conversations.length }
    };
    
  } catch (error) {
    Logger.log('❌ خطا در توجیه مدل: ' + error.message);
    return { success: false, error: error.message };
  }
}

function generatePersistentProjectBriefing(context) {
  const completedPhases = context.phases.filter(p => p.status === 'completed');
  const progressSummary = `از ${context.phases.length} فاز، ${completedPhases.length} فاز تکمیل شده. فاز فعلی: ${context.currentPhase.name}`;
  
  const keyDecisions = context.summary.keyDecisions || [];
  const currentChallenges = context.summary.currentChallenges || [];
  
  const importantFiles = context.files.generated.slice(-10).map(f => ({
    name: f.name, description: f.description || 'فایل تولید شده'
  }));
  
  const recentConversations = context.conversations.slice(-5).map(c => ({
    timestamp: c.timestamp, userInput: c.userInput, response: c.responses[0]?.response || ''
  }));
  
  return { progressSummary, keyDecisions: keyDecisions.slice(0, 10), currentChallenges: currentChallenges.slice(0, 5), importantFiles, recentConversations };
}

function hasPersistentApiKeyForModel(modelId) {
  const keys = getApiKeys();
  if (modelId.startsWith('gpt')) return !!keys.openai;
  if (modelId.startsWith('claude')) return !!keys.claude;
  if (modelId.startsWith('gemini')) return !!keys.gemini;
  if (modelId.startsWith('deepseek')) return !!keys.deepseek;
  if (modelId.includes('/')) return !!keys.openrouter;
  return false;
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 PERSISTENT PROJECT: FILE MANAGEMENT
// ═══════════════════════════════════════════════════════════════════════════════

function savePersistentProjectFile(projectId, fileName, content, fileType, category, description) {
  try {
    Logger.log('💾 ذخیره فایل: ' + fileName);
    
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    const projectFolder = DriveApp.getFolderById(projectInfo.folderId);
    
    let targetFolder;
    switch (category) {
      case 'code': targetFolder = getOrCreatePersistentFolder(projectFolder, '02_Generated/Code'); break;
      case 'document': targetFolder = getOrCreatePersistentFolder(projectFolder, '02_Generated/Documents'); break;
      case 'image': targetFolder = getOrCreatePersistentFolder(projectFolder, '02_Generated/Images'); break;
      case 'log': targetFolder = getOrCreatePersistentFolder(projectFolder, '04_Logs'); break;
      case 'test': targetFolder = getOrCreatePersistentFolder(projectFolder, '05_Tests'); break;
      case 'upload': targetFolder = getOrCreatePersistentFolder(projectFolder, '01_Uploads'); break;
      default: targetFolder = projectFolder;
    }
    
    const existingFiles = targetFolder.getFilesByName(fileName);
    let version = 1;
    if (existingFiles.hasNext()) {
      const versionsFolder = getOrCreatePersistentFolder(projectFolder, '03_Versions');
      const versionFolder = getOrCreatePersistentFolder(versionsFolder, 'v' + getNextPersistentVersion(versionsFolder));
      while (existingFiles.hasNext()) {
        const oldFile = existingFiles.next();
        oldFile.moveTo(versionFolder);
        version++;
      }
    }
    
    const mimeType = getPersistentMimeType(fileType);
    const newFile = targetFolder.createFile(fileName, content, mimeType);
    
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    context.files.generated.push({
      id: newFile.getId(), name: fileName, type: fileType, category: category,
      version: version, url: newFile.getUrl(), description: description,
      createdAt: new Date().toISOString(), size: newFile.getSize()
    });
    context.metrics.totalFiles++;
    
    contextFile.setContent(JSON.stringify(context, null, 2));
    
    const spreadsheet = SpreadsheetApp.openById(projectInfo.sheetId);
    const filesSheet = spreadsheet.getSheetByName(PERSISTENT_PROJECT_CONFIG.SHEETS.FILES_REGISTRY);
    filesSheet.appendRow([
      context.files.generated.length, fileName, fileType, category, 'v' + version,
      formatPersistentFileSize(newFile.getSize()), new Date().toLocaleString('fa-IR'),
      new Date().toLocaleString('fa-IR'), newFile.getUrl(), description
    ]);
    
    Logger.log('✅ فایل ذخیره شد: ' + newFile.getId());
    
    return { success: true, fileId: newFile.getId(), fileUrl: newFile.getUrl(), version: version, path: category + '/' + fileName };
    
  } catch (error) {
    Logger.log('❌ خطا در ذخیره فایل: ' + error.message);
    return { success: false, error: error.message };
  }
}

function syncPersistentProjectCode(projectId, codeType, code, description) {
  try {
    Logger.log('🔄 همگام‌سازی کد ' + codeType);
    
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    if (!context.codeSync) context.codeSync = { backend: {}, frontend: {} };
    
    const sync = context.codeSync[codeType] || {};
    sync.version = (sync.version || 0) + 1;
    sync.lastCode = code;
    sync.lastUpdate = new Date().toISOString();
    sync.description = description;
    context.codeSync[codeType] = sync;
    
    const fileName = codeType === 'backend' ? `Backend_v${sync.version}.gs` : `Frontend_v${sync.version}.html`;
    const result = savePersistentProjectFile(projectId, fileName, code, codeType === 'backend' ? 'javascript' : 'html', 'code', description);
    
    contextFile.setContent(JSON.stringify(context, null, 2));
    
    return { success: true, version: sync.version, fileResult: result };
    
  } catch (error) {
    Logger.log('❌ خطا در همگام‌سازی کد: ' + error.message);
    return { success: false, error: error.message };
  }
}

function savePersistentProjectLog(projectId, logContent, logType) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const fileName = `log_${logType}_${timestamp}.txt`;
  return savePersistentProjectFile(projectId, fileName, logContent, 'text', 'log', `لاگ ${logType} - ${new Date().toLocaleString('fa-IR')}`);
}

function getOrCreatePersistentFolder(parentFolder, path) {
  const parts = path.split('/');
  let currentFolder = parentFolder;
  for (const part of parts) {
    const folders = currentFolder.getFoldersByName(part);
    if (folders.hasNext()) currentFolder = folders.next();
    else currentFolder = currentFolder.createFolder(part);
  }
  return currentFolder;
}

function getNextPersistentVersion(versionsFolder) {
  let maxVersion = 0;
  const folders = versionsFolder.getFolders();
  while (folders.hasNext()) {
    const folder = folders.next();
    const match = folder.getName().match(/v(\d+)/);
    if (match) {
      const v = parseInt(match[1]);
      if (v > maxVersion) maxVersion = v;
    }
  }
  return maxVersion + 1;
}

function getPersistentMimeType(fileType) {
  const types = {
    'javascript': 'application/javascript', 'html': 'text/html', 'css': 'text/css',
    'json': 'application/json', 'text': 'text/plain', 'markdown': 'text/markdown',
    'python': 'text/x-python', 'xml': 'application/xml'
  };
  return types[fileType] || 'text/plain';
}

function formatPersistentFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 PERSISTENT PROJECT: DYNAMIC FLOWCHART
// ═══════════════════════════════════════════════════════════════════════════════

function generateFlowchartHtml(context, projectId) {
  const nodes = generatePersistentFlowchartNodes(context);
  
  return `<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>نمودار پروژه: ${context.project.name}</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/mermaid/10.6.1/mermaid.min.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Vazirmatn', 'Segoe UI', sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; padding: 20px; color: #fff; }
    .container { max-width: 1400px; margin: 0 auto; }
    .header { background: rgba(255,255,255,0.1); border-radius: 16px; padding: 24px; margin-bottom: 24px; backdrop-filter: blur(10px); }
    .header h1 { font-size: 28px; margin-bottom: 8px; }
    .header .meta { opacity: 0.8; font-size: 14px; }
    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 24px; }
    .stat-card { background: rgba(255,255,255,0.1); border-radius: 12px; padding: 16px; text-align: center; }
    .stat-card .value { font-size: 32px; font-weight: bold; }
    .stat-card .label { font-size: 12px; opacity: 0.8; }
    .flowchart-container { background: rgba(255,255,255,0.95); border-radius: 16px; padding: 24px; min-height: 400px; }
    .legend { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 24px; padding: 16px; background: rgba(255,255,255,0.1); border-radius: 12px; }
    .legend-item { display: flex; align-items: center; gap: 8px; }
    .legend-color { width: 20px; height: 20px; border-radius: 4px; }
    .mermaid { text-align: center; }
    .node-details { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: #fff; color: #333; padding: 24px; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto; z-index: 1000; }
    .node-details.active { display: block; }
    .overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 999; }
    .overlay.active { display: block; }
    .close-btn { position: absolute; top: 16px; left: 16px; background: #f44336; color: #fff; border: none; width: 32px; height: 32px; border-radius: 50%; cursor: pointer; font-size: 18px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🌳 ${context.project.name}</h1>
      <div class="meta">نوع: ${context.project.type} | ایجاد: ${new Date(context.project.createdAt).toLocaleDateString('fa-IR')} | آخرین به‌روزرسانی: ${new Date(context.project.updatedAt).toLocaleDateString('fa-IR')}</div>
    </div>
    <div class="stats">
      <div class="stat-card"><div class="value">${context.phases.length}</div><div class="label">فازها</div></div>
      <div class="stat-card"><div class="value">${context.phases.filter(p => p.status === 'completed').length}</div><div class="label">تکمیل شده</div></div>
      <div class="stat-card"><div class="value">${context.metrics.totalConversations}</div><div class="label">مکالمات</div></div>
      <div class="stat-card"><div class="value">${context.metrics.totalFiles}</div><div class="label">فایل‌ها</div></div>
    </div>
    <div class="flowchart-container"><div class="mermaid">${generatePersistentMermaidDiagram(context)}</div></div>
    <div class="legend">
      <div class="legend-item"><div class="legend-color" style="background: #4CAF50;"></div><span>تکمیل شده</span></div>
      <div class="legend-item"><div class="legend-color" style="background: #2196F3;"></div><span>در حال انجام</span></div>
      <div class="legend-item"><div class="legend-color" style="background: #9E9E9E;"></div><span>در انتظار</span></div>
      <div class="legend-item"><div class="legend-color" style="background: #F44336;"></div><span>ناموفق</span></div>
      <div class="legend-item"><div class="legend-color" style="background: #FF9800;"></div><span>متوقف</span></div>
      <div class="legend-item"><div class="legend-color" style="background: #9C27B0;"></div><span>برگشت</span></div>
    </div>
  </div>
  <div class="overlay" onclick="closeDetails()"></div>
  <div class="node-details" id="nodeDetails"><button class="close-btn" onclick="closeDetails()">×</button><div id="detailsContent"></div></div>
  <script>
    mermaid.initialize({ startOnLoad: true, theme: 'default', flowchart: { curve: 'basis', padding: 20 } });
    const nodesData = ${JSON.stringify(nodes)};
    document.addEventListener('click', function(e) {
      const node = e.target.closest('.node');
      if (node) showNodeDetails(node.id);
    });
    function showNodeDetails(nodeId) {
      const node = nodesData.find(n => n.id === nodeId);
      if (!node) return;
      document.getElementById('detailsContent').innerHTML = '<h2>'+node.name+'</h2><p><strong>وضعیت:</strong> '+node.statusLabel+'</p><p><strong>توضیحات:</strong> '+(node.description || '-')+'</p>';
      document.querySelector('.overlay').classList.add('active');
      document.getElementById('nodeDetails').classList.add('active');
    }
    function closeDetails() {
      document.querySelector('.overlay').classList.remove('active');
      document.getElementById('nodeDetails').classList.remove('active');
    }
  </script>
</body>
</html>`;
}

function generatePersistentFlowchartNodes(context) {
  const nodes = [{ id: 'start', name: '🚀 شروع پروژه', type: 'start', status: 'completed', statusLabel: 'تکمیل شده' }];
  
  for (const phase of context.phases) {
    const statusConfig = PERSISTENT_PROJECT_CONFIG.PHASE_STATUS[phase.status.toUpperCase()] || PERSISTENT_PROJECT_CONFIG.PHASE_STATUS.PENDING;
    nodes.push({
      id: phase.id, name: phase.name, type: 'phase', status: phase.status,
      statusLabel: statusConfig.label, color: statusConfig.color,
      description: phase.description, steps: phase.steps, progress: phase.progress
    });
  }
  
  const allCompleted = context.phases.every(p => p.status === 'completed');
  nodes.push({ id: 'end', name: '🏁 پایان پروژه', type: 'end', status: allCompleted ? 'completed' : 'pending', statusLabel: allCompleted ? 'تکمیل شده' : 'در انتظار' });
  
  return nodes;
}

function generatePersistentMermaidDiagram(context) {
  let diagram = 'flowchart TB\n';
  diagram += '  classDef completed fill:#4CAF50,stroke:#2E7D32,color:#fff\n';
  diagram += '  classDef inProgress fill:#2196F3,stroke:#1565C0,color:#fff\n';
  diagram += '  classDef pending fill:#9E9E9E,stroke:#616161,color:#fff\n';
  diagram += '  classDef failed fill:#F44336,stroke:#C62828,color:#fff\n';
  diagram += '  classDef paused fill:#FF9800,stroke:#EF6C00,color:#fff\n';
  diagram += '  classDef rollback fill:#9C27B0,stroke:#6A1B9A,color:#fff\n';
  diagram += '  classDef startEnd fill:#673AB7,stroke:#4527A0,color:#fff\n\n';
  
  diagram += '  start((🚀 شروع)):::startEnd\n';
  
  for (const phase of context.phases) {
    const label = phase.name.replace(/"/g, "'");
    let shape = `[${label}]`;
    if (phase.status === 'in_progress') shape = `[/${label}/]`;
    else if (phase.status === 'failed') shape = `{{${label}}}`;
    diagram += `  ${phase.id}${shape}:::${getPersistentStatusClass(phase.status)}\n`;
  }
  
  const allCompleted = context.phases.every(p => p.status === 'completed');
  diagram += `  endNode((🏁 پایان)):::${allCompleted ? 'completed' : 'pending'}\n\n`;
  
  if (context.phases.length > 0) {
    diagram += `  start --> ${context.phases[0].id}\n`;
    for (let i = 0; i < context.phases.length - 1; i++) {
      diagram += `  ${context.phases[i].id} --> ${context.phases[i + 1].id}\n`;
    }
    diagram += `  ${context.phases[context.phases.length - 1].id} --> endNode\n`;
  } else {
    diagram += '  start --> endNode\n';
  }
  
  return diagram;
}

function getPersistentStatusClass(status) {
  return { 'completed': 'completed', 'in_progress': 'inProgress', 'pending': 'pending', 'failed': 'failed', 'paused': 'paused', 'rollback': 'rollback' }[status] || 'pending';
}

function updatePersistentFlowchart(projectInfo, context) {
  try {
    const flowchartHtml = generateFlowchartHtml(context, projectInfo.id);
    const flowchartFile = DriveApp.getFileById(projectInfo.flowchartFileId);
    flowchartFile.setContent(flowchartHtml);
    context.tree.lastUpdate = new Date().toISOString();
    Logger.log('🌳 فلوچارت به‌روز شد');
  } catch (error) {
    Logger.log('⚠️ خطا در به‌روزرسانی فلوچارت: ' + error.message);
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 PERSISTENT PROJECT: PHASE MANAGEMENT
// ═══════════════════════════════════════════════════════════════════════════════

function startPersistentNextPhase(projectId) {
  try {
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    const currentIndex = context.phases.findIndex(p => p.id === context.currentPhase.id);
    
    if (currentIndex >= 0) {
      context.phases[currentIndex].status = 'completed';
      context.phases[currentIndex].progress = 100;
      context.phases[currentIndex].completedAt = new Date().toISOString();
    }
    
    if (currentIndex < context.phases.length - 1) {
      const nextPhase = context.phases[currentIndex + 1];
      nextPhase.status = 'in_progress';
      nextPhase.startedAt = new Date().toISOString();
      
      context.currentPhase = {
        id: nextPhase.id, name: nextPhase.name, step: 0,
        totalSteps: nextPhase.steps.length, status: 'in_progress'
      };
      
      contextFile.setContent(JSON.stringify(context, null, 2));
      
      const spreadsheet = SpreadsheetApp.openById(projectInfo.sheetId);
      updatePersistentPhasesSheet(spreadsheet, context);
      addPersistentTimelineEvent(spreadsheet, 'شروع فاز جدید', 'phase', nextPhase.id, nextPhase.name, 'System');
      updatePersistentDashboard(spreadsheet, context);
      updatePersistentFlowchart(projectInfo, context);
      
      return {
        success: true, previousPhase: context.phases[currentIndex].name,
        currentPhase: nextPhase.name, remainingPhases: context.phases.length - currentIndex - 2
      };
    } else {
      context.project.status = 'completed';
      context.project.completedAt = new Date().toISOString();
      contextFile.setContent(JSON.stringify(context, null, 2));
      
      return { success: true, completed: true, message: 'پروژه با موفقیت تکمیل شد!' };
    }
    
  } catch (error) {
    Logger.log('❌ خطا در شروع فاز بعدی: ' + error.message);
    return { success: false, error: error.message };
  }
}

function rollbackPersistentPhase(projectId, reason) {
  try {
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    const currentIndex = context.phases.findIndex(p => p.id === context.currentPhase.id);
    if (currentIndex <= 0) return { success: false, error: 'فاز قبلی وجود ندارد' };
    
    context.phases[currentIndex].status = 'rollback';
    context.phases[currentIndex].rollbackReason = reason;
    context.phases[currentIndex].rollbackAt = new Date().toISOString();
    
    const prevPhase = context.phases[currentIndex - 1];
    prevPhase.status = 'in_progress';
    
    context.currentPhase = {
      id: prevPhase.id, name: prevPhase.name, step: 0,
      totalSteps: prevPhase.steps.length, status: 'in_progress'
    };
    
    contextFile.setContent(JSON.stringify(context, null, 2));
    
    const spreadsheet = SpreadsheetApp.openById(projectInfo.sheetId);
    addPersistentTimelineEvent(spreadsheet, 'برگشت به فاز قبلی', 'rollback', prevPhase.id, `دلیل: ${reason}`, 'System');
    updatePersistentFlowchart(projectInfo, context);
    
    return { success: true, rolledBackFrom: context.phases[currentIndex].name, currentPhase: prevPhase.name, reason: reason };
    
  } catch (error) {
    Logger.log('❌ خطا در برگشت فاز: ' + error.message);
    return { success: false, error: error.message };
  }
}

function updatePersistentPhaseProgress(projectId, progress, stepCompleted) {
  try {
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    const currentIndex = context.phases.findIndex(p => p.id === context.currentPhase.id);
    if (currentIndex >= 0) {
      context.phases[currentIndex].progress = progress;
      if (stepCompleted) context.currentPhase.step++;
      contextFile.setContent(JSON.stringify(context, null, 2));
      
      const spreadsheet = SpreadsheetApp.openById(projectInfo.sheetId);
      updatePersistentPhasesSheet(spreadsheet, context);
      updatePersistentDashboard(spreadsheet, context);
    }
    
    return { success: true, progress: progress };
    
  } catch (error) {
    return { success: false, error: error.message };
  }
}

function updatePersistentPhasesSheet(spreadsheet, context) {
  const phasesSheet = spreadsheet.getSheetByName(PERSISTENT_PROJECT_CONFIG.SHEETS.PHASES);
  const lastRow = phasesSheet.getLastRow();
  if (lastRow > 1) phasesSheet.getRange(2, 1, lastRow - 1, 9).clearContent();
  
  const phasesData = context.phases.map((p, i) => {
    const statusConfig = PERSISTENT_PROJECT_CONFIG.PHASE_STATUS[p.status.toUpperCase()] || PERSISTENT_PROJECT_CONFIG.PHASE_STATUS.PENDING;
    return [
      i + 1, p.name, p.description || '', statusConfig.label, p.progress + '%',
      p.startedAt ? new Date(p.startedAt).toLocaleDateString('fa-IR') : '-',
      p.completedAt ? new Date(p.completedAt).toLocaleDateString('fa-IR') : '-', '', ''
    ];
  });
  
  if (phasesData.length > 0) phasesSheet.getRange(2, 1, phasesData.length, 9).setValues(phasesData);
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 PERSISTENT PROJECT: AI INTERACTION
// ═══════════════════════════════════════════════════════════════════════════════

function sendPersistentProjectMessage(projectId, userMessage, options = {}) {
  try {
    Logger.log('💬 پیام پروژه: ' + projectId);
    
    const projectData = loadPersistentProject(projectId);
    if (!projectData.success) return { success: false, error: projectData.error };
    
    const context = projectData.context;
    
    let selectedModel = options.model;
    if (!selectedModel || options.autoSelect) {
      const modelSelection = selectBestPersistentModel(projectId, userMessage, options.complexity);
      selectedModel = modelSelection.selectedModel;
      if (modelSelection.suggestUpgrade) {
        Logger.log('⚠️ پیشنهاد ارتقا به: ' + modelSelection.suggestedModel);
      }
    }
    
    // ✅ v16.0: ساخت Context کامل با محتوای فایل‌ها
    const fullContext = buildFullProjectContext(projectId, context, options);
    const systemPrompt = buildEnhancedSystemPrompt(fullContext);
    const finalPrompt = `${systemPrompt}\n\n---\n\n## 📝 درخواست کاربر:\n${userMessage}`;
    
    const startTime = Date.now();
    const response = callModel(selectedModel, finalPrompt, options.attachments || []);
    const duration = (Date.now() - startTime) / 1000;
    
    // ✅ v16.0: پردازش و فرمت‌بندی پاسخ
    const formattedResponse = formatModelResponse(response, selectedModel);
    
    const initialScore = 75;
    const modelResponses = [{ model: selectedModel, response: formattedResponse, score: initialScore, duration: duration }];
    
    addPersistentProjectConversation(projectId, userMessage, modelResponses);
    
    // ✅ v16.0: به‌روزرسانی شیت‌ها
    updateProjectSheets(projectId, context, userMessage, formattedResponse);
    
    const codeBlocks = extractPersistentCodeFromResponse(response);
    if (codeBlocks.length > 0) {
      for (const block of codeBlocks) {
        savePersistentProjectFile(projectId, 
          `code_${Date.now()}.${getPersistentExtensionForLanguage(block.language)}`,
          block.code, block.language, 'code', 'کد استخراج شده از پاسخ AI');
      }
    }
    
    return {
      success: true, model: selectedModel, response: formattedResponse,
      duration: duration, codeBlocks: codeBlocks, currentPhase: context.currentPhase
    };
    
  } catch (error) {
    Logger.log('❌ خطا در ارسال پیام پروژه: ' + error.message);
    return { success: false, error: error.message };
  }
}

/**
 * ✅ v16.0: ساخت Context کامل پروژه با محتوای فایل‌ها
 */
function buildFullProjectContext(projectId, context, options) {
  const fullContext = {
    project: context.project,
    currentPhase: context.currentPhase,
    phases: context.phases,
    conversations: context.conversations,
    files: {
      uploaded: [],
      generated: context.files?.generated || []
    },
    learnings: [],
    roadmap: null
  };
  
  // خواندن محتوای فایل‌های آپلود شده
  try {
    const registry = getPersistentProjectRegistry();
    const projectMeta = registry.projects[projectId];
    
    if (projectMeta && projectMeta.folderId) {
      const folder = DriveApp.getFolderById(projectMeta.folderId);
      const files = folder.getFiles();
      
      while (files.hasNext()) {
        const file = files.next();
        const fileName = file.getName();
        const mimeType = file.getMimeType();
        const fileSize = file.getSize();
        
        // فقط فایل‌های متنی و کوچکتر از 500KB را بخوان
        if (fileSize < 500000 && isTextFile(mimeType, fileName)) {
          try {
            const content = file.getBlob().getDataAsString();
            fullContext.files.uploaded.push({
              name: fileName,
              type: mimeType,
              size: fileSize,
              content: content.substring(0, 50000), // حداکثر 50K کاراکتر
              fullContent: content.length <= 50000
            });
          } catch (e) {
            fullContext.files.uploaded.push({
              name: fileName,
              type: mimeType,
              size: fileSize,
              content: null,
              error: 'خطا در خواندن فایل'
            });
          }
        } else {
          fullContext.files.uploaded.push({
            name: fileName,
            type: mimeType,
            size: fileSize,
            content: null,
            reason: fileSize >= 500000 ? 'فایل بزرگ' : 'فایل باینری'
          });
        }
      }
    }
  } catch (e) {
    Logger.log('⚠️ خطا در خواندن فایل‌ها: ' + e);
  }
  
  // خواندن آموزش‌ها و قواعد (اگر وجود دارد)
  fullContext.learnings = extractLearningsFromFiles(fullContext.files.uploaded);
  
  return fullContext;
}

/**
 * ✅ v16.0: تشخیص فایل متنی
 */
function isTextFile(mimeType, fileName) {
  const textMimes = [
    'text/plain', 'text/html', 'text/css', 'text/javascript',
    'text/markdown', 'text/csv', 'application/json', 'application/xml',
    'application/javascript', 'text/x-python', 'text/x-java',
    'application/x-httpd-php'
  ];
  
  const textExtensions = [
    '.txt', '.md', '.html', '.css', '.js', '.ts', '.py', '.java',
    '.json', '.xml', '.csv', '.gs', '.jsx', '.tsx', '.vue', '.php',
    '.sql', '.sh', '.bash', '.yml', '.yaml', '.env', '.config',
    '.gitignore', '.htaccess', '.log'
  ];
  
  if (textMimes.some(m => mimeType.includes(m))) return true;
  if (textExtensions.some(ext => fileName.toLowerCase().endsWith(ext))) return true;
  
  return false;
}

/**
 * ✅ v16.0: استخراج آموزش‌ها و قواعد از فایل‌ها
 */
function extractLearningsFromFiles(files) {
  const learnings = [];
  
  for (const file of files) {
    if (!file.content) continue;
    
    const lowerName = file.name.toLowerCase();
    
    // فایل‌هایی که آموزش یا قواعد هستند
    if (lowerName.includes('rule') || lowerName.includes('قواعد') ||
        lowerName.includes('guide') || lowerName.includes('راهنما') ||
        lowerName.includes('learn') || lowerName.includes('آموزش') ||
        lowerName.includes('instruction') || lowerName.includes('دستورالعمل')) {
      learnings.push({
        source: file.name,
        type: 'learning',
        content: file.content
      });
    }
  }
  
  return learnings;
}

/**
 * ✅ v16.0: ساخت System Prompt بهبود یافته
 */
function buildEnhancedSystemPrompt(fullContext) {
  let prompt = `# 🎯 اتاق مهندسی پروژه

شما یک مهندس پروژه هوشمند هستید که به کاربر کمک می‌کنید پروژه‌اش را مدیریت و پیش ببرد.

## 📋 اطلاعات پروژه
- **نام:** ${fullContext.project.name}
- **نوع:** ${fullContext.project.type}
- **هدف:** ${fullContext.project.goal || 'تعریف نشده'}
- **پیچیدگی:** ${fullContext.project.complexity}

## 📍 وضعیت فعلی
- **فاز جاری:** ${fullContext.currentPhase.name}
- **مرحله:** ${fullContext.currentPhase.step} از ${fullContext.currentPhase.totalSteps}
- **پیشرفت:** ${fullContext.currentPhase.progress || 0}%

## 🗺️ نقشه راه
`;

  // فازهای پروژه
  fullContext.phases.forEach((phase, i) => {
    const status = phase.status || 'pending';
    const icon = status === 'completed' ? '✅' : status === 'in_progress' ? '🔄' : '⏳';
    prompt += `${i + 1}. ${icon} **${phase.name}** - ${status}\n`;
  });

  // فایل‌های آپلود شده با محتوا
  if (fullContext.files.uploaded.length > 0) {
    prompt += `\n## 📁 فایل‌های پروژه (${fullContext.files.uploaded.length} فایل)\n`;
    
    for (const file of fullContext.files.uploaded) {
      prompt += `\n### 📄 ${file.name}\n`;
      
      if (file.content) {
        prompt += `**نوع:** ${file.type} | **حجم:** ${Math.round(file.size/1024)}KB\n`;
        prompt += `\`\`\`\n${file.content}\n\`\`\`\n`;
        
        if (!file.fullContent) {
          prompt += `⚠️ *این فایل خلاصه شده است (بخش اول)*\n`;
        }
      } else {
        prompt += `**وضعیت:** ${file.reason || file.error || 'محتوا در دسترس نیست'}\n`;
      }
    }
  }

  // آموزش‌ها و قواعد
  if (fullContext.learnings.length > 0) {
    prompt += `\n## 📚 آموزش‌ها و قواعد\n`;
    for (const learning of fullContext.learnings) {
      prompt += `\n### از فایل: ${learning.source}\n`;
      prompt += `${learning.content}\n`;
    }
  }

  // مکالمات اخیر
  if (fullContext.conversations.length > 0) {
    const recent = fullContext.conversations.slice(-3);
    prompt += `\n## 💬 مکالمات اخیر\n`;
    for (const conv of recent) {
      const userText = (conv.userInput || '').substring(0, 500);
      prompt += `\n**کاربر:** ${userText}\n`;
      if (conv.responses && conv.responses[0]) {
        const resp = conv.responses[0].response;
        const respText = typeof resp === 'string' ? resp.substring(0, 500) : JSON.stringify(resp).substring(0, 500);
        prompt += `**پاسخ:** ${respText}...\n`;
      }
    }
  }

  prompt += `
## 📌 دستورالعمل‌های پاسخ‌دهی

1. **پاسخ ساختاریافته:** پاسخ‌ها را با عنوان و بخش‌بندی واضح ارائه دهید
2. **کد کامل:** کدها را کامل و قابل اجرا بنویسید، نه خلاصه
3. **دستورات واضح:** اگر کاربر باید در محیط دیگری (مثل Terminal) کاری انجام دهد، دستورات را واضح بنویسید
4. **گام به گام:** مراحل را شماره‌گذاری کنید
5. **توجه به Context:** به تمام فایل‌ها و سوابق توجه کنید
6. **بدون توضیح زائد:** مستقیم به اصل مطلب بپردازید

## 🎯 وظیفه شما
- تحلیل فایل‌ها و کدهای موجود
- تشخیص وضعیت فعلی پروژه
- پیشنهاد گام بعدی
- ارائه کد و دستورات لازم
- راهنمایی اجرا در محیط‌های خارجی (Google Console، Terminal، ...)
`;

  return prompt;
}

/**
 * ✅ v16.0: فرمت‌بندی پاسخ مدل
 */
function formatModelResponse(response, modelName) {
  if (!response) return 'پاسخی دریافت نشد';
  
  // اگر JSON است، فرمت کن
  try {
    if (typeof response === 'object') {
      return JSON.stringify(response, null, 2);
    }
  } catch (e) {}
  
  // حذف کاراکترهای اضافی
  let formatted = response.toString();
  
  // اگر با { شروع می‌شود، احتمالاً JSON نامعتبر است
  if (formatted.startsWith('{') || formatted.startsWith('[')) {
    try {
      const parsed = JSON.parse(formatted);
      if (parsed.response) return parsed.response;
      if (parsed.content) return parsed.content;
      if (parsed.text) return parsed.text;
    } catch (e) {}
  }
  
  return formatted;
}

/**
 * ✅ v16.0: به‌روزرسانی شیت‌های پروژه
 */
function updateProjectSheets(projectId, context, userMessage, response) {
  try {
    const registry = getPersistentProjectRegistry();
    const projectMeta = registry.projects[projectId];
    
    if (!projectMeta || !projectMeta.folderId) return;
    
    const folder = DriveApp.getFolderById(projectMeta.folderId);
    
    // به‌روزرسانی شیت Project_Master
    updateMasterSheet(folder, context, userMessage, response);
    
    // به‌روزرسانی شیت Conversations
    updateConversationsSheet(folder, userMessage, response, context.currentPhase);
    
    // به‌روزرسانی شیت Phases
    updatePhasesSheet(folder, context.phases);
    
  } catch (e) {
    Logger.log('⚠️ خطا در به‌روزرسانی شیت‌ها: ' + e);
  }
}

/**
 * ✅ v16.0: به‌روزرسانی شیت اصلی
 */
function updateMasterSheet(folder, context, lastMessage, lastResponse) {
  try {
    const files = folder.getFilesByName('Project_Master');
    if (!files.hasNext()) return;
    
    const file = files.next();
    const ss = SpreadsheetApp.open(file);
    const sheet = ss.getSheetByName('Overview') || ss.getSheets()[0];
    
    // به‌روزرسانی اطلاعات
    const data = [
      ['آخرین به‌روزرسانی', new Date().toLocaleString('fa-IR')],
      ['فاز فعلی', context.currentPhase.name],
      ['پیشرفت کلی', calculateOverallProgress(context.phases) + '%'],
      ['تعداد مکالمات', context.conversations.length],
      ['آخرین پیام', lastMessage.substring(0, 100)],
      ['وضعیت', 'فعال']
    ];
    
    // پیدا کردن یا ایجاد بخش به‌روزرسانی
    const lastRow = sheet.getLastRow();
    sheet.getRange(lastRow + 2, 1, data.length, 2).setValues(data);
    
  } catch (e) {
    Logger.log('⚠️ خطا در به‌روزرسانی Master: ' + e);
  }
}

/**
 * ✅ v16.0: به‌روزرسانی شیت مکالمات
 */
function updateConversationsSheet(folder, message, response, phase) {
  try {
    const files = folder.getFilesByName('Conversations');
    let ss, sheet;
    
    if (files.hasNext()) {
      ss = SpreadsheetApp.open(files.next());
      sheet = ss.getSheets()[0];
    } else {
      // ایجاد شیت جدید
      ss = SpreadsheetApp.create('Conversations');
      sheet = ss.getSheets()[0];
      sheet.appendRow(['تاریخ', 'فاز', 'پیام کاربر', 'پاسخ AI']);
      
      // انتقال به فولدر پروژه
      const ssFile = DriveApp.getFileById(ss.getId());
      folder.addFile(ssFile);
      DriveApp.getRootFolder().removeFile(ssFile);
    }
    
    // اضافه کردن ردیف جدید
    sheet.appendRow([
      new Date().toLocaleString('fa-IR'),
      phase.name,
      message.substring(0, 500),
      (response || '').substring(0, 1000)
    ]);
    
  } catch (e) {
    Logger.log('⚠️ خطا در به‌روزرسانی Conversations: ' + e);
  }
}

/**
 * ✅ v16.0: به‌روزرسانی شیت فازها
 */
function updatePhasesSheet(folder, phases) {
  try {
    const files = folder.getFilesByName('Phases');
    let ss, sheet;
    
    if (files.hasNext()) {
      ss = SpreadsheetApp.open(files.next());
      sheet = ss.getSheets()[0];
    } else {
      ss = SpreadsheetApp.create('Phases');
      sheet = ss.getSheets()[0];
      sheet.appendRow(['شماره', 'نام فاز', 'وضعیت', 'پیشرفت', 'شروع', 'پایان']);
      
      const ssFile = DriveApp.getFileById(ss.getId());
      folder.addFile(ssFile);
      DriveApp.getRootFolder().removeFile(ssFile);
    }
    
    // پاک کردن و نوشتن مجدد
    if (sheet.getLastRow() > 1) {
      sheet.getRange(2, 1, sheet.getLastRow() - 1, 6).clear();
    }
    
    phases.forEach((phase, i) => {
      sheet.appendRow([
        i + 1,
        phase.name,
        phase.status || 'pending',
        (phase.progress || 0) + '%',
        phase.startedAt || '-',
        phase.completedAt || '-'
      ]);
    });
    
  } catch (e) {
    Logger.log('⚠️ خطا در به‌روزرسانی Phases: ' + e);
  }
}

/**
 * ✅ v16.0: محاسبه پیشرفت کلی
 */
function calculateOverallProgress(phases) {
  if (!phases || phases.length === 0) return 0;
  
  let completed = 0;
  let inProgress = 0;
  
  for (const phase of phases) {
    if (phase.status === 'completed') completed++;
    else if (phase.status === 'in_progress') inProgress += 0.5;
  }
  
  return Math.round(((completed + inProgress) / phases.length) * 100);
}

function buildPersistentProjectSystemPrompt(context, includeHistory = true) {
  // این تابع برای سازگاری با کدهای قدیمی نگه داشته شده
  return buildEnhancedSystemPrompt({
    project: context.project,
    currentPhase: context.currentPhase,
    phases: context.phases,
    conversations: context.conversations,
    files: { uploaded: [], generated: context.files?.generated || [] },
    learnings: []
  });
}

function extractPersistentCodeFromResponse(response) {
  const codeBlocks = [];
  const regex = /```(\w+)?\n([\s\S]*?)```/g;
  let match;
  while ((match = regex.exec(response)) !== null) {
    codeBlocks.push({ language: match[1] || 'text', code: match[2].trim() });
  }
  return codeBlocks;
}

function getPersistentExtensionForLanguage(language) {
  const extensions = {
    'javascript': 'js', 'js': 'js', 'typescript': 'ts', 'ts': 'ts',
    'python': 'py', 'html': 'html', 'css': 'css', 'json': 'json',
    'sql': 'sql', 'bash': 'sh', 'shell': 'sh', 'java': 'java',
    'cpp': 'cpp', 'c': 'c', 'go': 'go', 'rust': 'rs', 'php': 'php'
  };
  return extensions[language?.toLowerCase()] || 'txt';
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 PERSISTENT PROJECT: API ENDPOINTS FOR FRONTEND
// ═══════════════════════════════════════════════════════════════════════════════

function apiGetPersistentProjects() { return getPersistentProjects(); }

function apiCreateProject(config) { return createPersistentProject(config); }

function apiLoadProject(projectId) { return loadPersistentProject(projectId); }

function apiSendProjectMessage(projectId, message, options) { 
  return sendPersistentProjectMessage(projectId, message, options); 
}

function apiNextPhase(projectId) { return startPersistentNextPhase(projectId); }

function apiRollbackPhase(projectId, reason) { return rollbackPersistentPhase(projectId, reason); }

function apiUpdateProgress(projectId, progress, stepCompleted) { 
  return updatePersistentPhaseProgress(projectId, progress, stepCompleted); 
}

function apiReplaceModel(projectId, oldModel, newModel, reason) { 
  return replacePersistentWeakModel(projectId, oldModel, newModel, reason); 
}

function apiAddModelToProject(projectId, modelId) {
  try {
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    if (!context.models.active.includes(modelId)) {
      context.models.active.push(modelId);
      const briefing = briefPersistentNewModel(projectId, modelId);
      contextFile.setContent(JSON.stringify(context, null, 2));
      return { success: true, modelId: modelId, activeModels: context.models.active, briefing: briefing };
    }
    return { success: true, message: 'مدل قبلاً اضافه شده' };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

function apiRemoveModelFromProject(projectId, modelId) {
  try {
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    context.models.active = context.models.active.filter(m => m !== modelId);
    contextFile.setContent(JSON.stringify(context, null, 2));
    
    return { success: true, removedModel: modelId, activeModels: context.models.active };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

function apiSaveProjectFile(projectId, fileName, content, fileType, category, description) {
  return savePersistentProjectFile(projectId, fileName, content, fileType, category, description);
}

function apiSaveLog(projectId, logContent, logType) {
  return savePersistentProjectLog(projectId, logContent, logType);
}

function apiSyncCode(projectId, codeType, code, description) {
  return syncPersistentProjectCode(projectId, codeType, code, description);
}

function apiScoreResponse(projectId, conversationId, modelId, scores) {
  try {
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    const conv = context.conversations.find(c => c.id === conversationId);
    if (!conv) return { success: false, error: 'مکالمه یافت نشد' };
    
    const response = conv.responses.find(r => r.model === modelId);
    if (!response) return { success: false, error: 'پاسخ مدل یافت نشد' };
    
    const criteria = MODEL_SCORING_SYSTEM.CRITERIA;
    let totalScore = 0;
    for (const [key, config] of Object.entries(criteria)) {
      totalScore += (scores[key.toLowerCase()] || 0) * config.weight;
    }
    
    response.score = Math.round(totalScore);
    response.detailedScores = scores;
    
    updatePersistentModelScore(context, modelId, response.score, context.project.type);
    contextFile.setContent(JSON.stringify(context, null, 2));
    
    const spreadsheet = SpreadsheetApp.openById(projectInfo.sheetId);
    const modelsSheet = spreadsheet.getSheetByName(PERSISTENT_PROJECT_CONFIG.SHEETS.MODELS_PERFORMANCE);
    updatePersistentModelPerformanceSheet(modelsSheet, modelId, context.project.type, context.models.scores[modelId]);
    
    return { success: true, finalScore: response.score, modelAverage: context.models.scores[modelId].average };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

function updatePersistentModelPerformanceSheet(sheet, modelId, projectType, scoreData) {
  const data = sheet.getDataRange().getValues();
  let rowIndex = -1;
  for (let i = 1; i < data.length; i++) {
    if (data[i][0] === modelId && data[i][2] === projectType) { rowIndex = i + 1; break; }
  }
  
  const rowData = [
    modelId, getPersistentModelProvider(modelId), projectType,
    scoreData.byType[projectType]?.average || '-', '-', '-', '-', '-',
    scoreData.average, scoreData.count, new Date().toLocaleString('fa-IR')
  ];
  
  if (rowIndex > 0) sheet.getRange(rowIndex, 1, 1, 11).setValues([rowData]);
  else sheet.appendRow(rowData);
}

function apiGetProjectSummary(projectId) {
  try {
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    const briefing = generatePersistentProjectBriefing(context);
    
    return {
      success: true, project: context.project, currentPhase: context.currentPhase,
      phases: context.phases, models: context.models, metrics: context.metrics, briefing: briefing
    };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

function apiUpdateSummary(projectId, summaryData) {
  try {
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    context.summary = { ...context.summary, ...summaryData, lastUpdate: new Date().toISOString() };
    contextFile.setContent(JSON.stringify(context, null, 2));
    
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

function apiGetProjectStructure(projectId) {
  try {
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    const folder = DriveApp.getFolderById(projectInfo.folderId);
    return { success: true, structure: getPersistentFolderStructure(folder), folderUrl: folder.getUrl() };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

function apiAddCustomPhase(projectId, phaseName, description, steps, insertAfter) {
  try {
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    const newPhase = {
      id: 'phase_custom_' + Date.now(), name: phaseName,
      description: description, status: 'pending', steps: steps || [], progress: 0
    };
    
    if (insertAfter) {
      const index = context.phases.findIndex(p => p.id === insertAfter);
      if (index >= 0) context.phases.splice(index + 1, 0, newPhase);
      else context.phases.push(newPhase);
    } else {
      context.phases.push(newPhase);
    }
    
    contextFile.setContent(JSON.stringify(context, null, 2));
    
    const spreadsheet = SpreadsheetApp.openById(projectInfo.sheetId);
    updatePersistentPhasesSheet(spreadsheet, context);
    updatePersistentFlowchart(projectInfo, context);
    
    return { success: true, phase: newPhase, totalPhases: context.phases.length };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

function apiDeleteProject(projectId, deleteFiles = false) {
  try {
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    if (!projectInfo) return { success: false, error: 'پروژه یافت نشد' };
    
    if (deleteFiles) {
      const folder = DriveApp.getFolderById(projectInfo.folderId);
      folder.setTrashed(true);
    }
    
    delete registry[projectId];
    savePersistentProjectRegistry(registry);
    
    return { success: true, message: deleteFiles ? 'پروژه و فایل‌ها حذف شدند' : 'پروژه از لیست حذف شد' };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * ویرایش اطلاعات پروژه
 */
function apiUpdateProject(projectId, updates) {
  try {
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    if (!projectInfo) return { success: false, error: 'پروژه یافت نشد' };
    
    // به‌روزرسانی context
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    // به‌روزرسانی فیلدها
    if (updates.name) {
      context.project.name = updates.name;
      registry[projectId].name = updates.name;
    }
    if (updates.description) context.project.description = updates.description;
    if (updates.goal) context.project.goal = updates.goal;
    if (updates.type) context.project.type = updates.type;
    if (updates.complexity) context.project.complexity = updates.complexity;
    
    context.updatedAt = new Date().toISOString();
    registry[projectId].updatedAt = context.updatedAt;
    
    // ذخیره
    contextFile.setContent(JSON.stringify(context, null, 2));
    savePersistentProjectRegistry(registry);
    
    return { success: true, message: 'پروژه به‌روزرسانی شد' };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

function apiUploadToProject(projectId, fileName, fileContent, mimeType) {
  try {
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    const projectFolder = DriveApp.getFolderById(projectInfo.folderId);
    const uploadsFolder = getOrCreatePersistentFolder(projectFolder, '01_Uploads');
    
    const file = uploadsFolder.createFile(
      Utilities.newBlob(Utilities.base64Decode(fileContent), mimeType, fileName)
    );
    
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    context.files.uploaded.push({
      id: file.getId(), name: fileName, mimeType: mimeType,
      url: file.getUrl(), uploadedAt: new Date().toISOString(), size: file.getSize()
    });
    
    contextFile.setContent(JSON.stringify(context, null, 2));
    
    const spreadsheet = SpreadsheetApp.openById(projectInfo.sheetId);
    const filesSheet = spreadsheet.getSheetByName(PERSISTENT_PROJECT_CONFIG.SHEETS.FILES_REGISTRY);
    filesSheet.appendRow([
      context.files.uploaded.length + context.files.generated.length,
      fileName, mimeType.split('/')[1] || 'unknown', 'Uploads', 'v1',
      formatPersistentFileSize(file.getSize()), new Date().toLocaleString('fa-IR'),
      new Date().toLocaleString('fa-IR'), file.getUrl(), 'فایل آپلود شده'
    ]);
    
    return { success: true, fileId: file.getId(), fileUrl: file.getUrl() };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

function apiGetConversationHistory(projectId, page, perPage) {
  page = page || 1;
  perPage = perPage || 20;
  try {
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    const start = (page - 1) * perPage;
    const conversations = context.conversations.slice().reverse().slice(start, start + perPage);
    
    return {
      success: true, conversations: conversations, total: context.conversations.length,
      page: page, perPage: perPage, totalPages: Math.ceil(context.conversations.length / perPage)
    };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

function apiGetModelScores(projectId) {
  try {
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    const scores = Object.entries(context.models.scores).map(([modelId, scoreData]) => ({
      modelId, provider: getPersistentModelProvider(modelId),
      average: scoreData.average, count: scoreData.count, byType: scoreData.byType
    }));
    
    scores.sort((a, b) => b.average - a.average);
    
    return {
      success: true, scores: scores, activeModels: context.models.active,
      needsReplacement: context.models.needsReplacement || []
    };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 PERSISTENT PROJECT: TEST FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

function testCreatePersistentProject() {
  const result = createPersistentProject({
    name: 'پروژه تست', type: 'coding',
    description: 'این یک پروژه تست است', goal: 'تست عملکرد سیستم',
    complexity: 'intermediate', models: ['gpt-4-turbo', 'claude-sonnet-4-20250514']
  });
  Logger.log(JSON.stringify(result, null, 2));
  return result;
}

function testLoadPersistentProject() {
  const projects = getPersistentProjects();
  if (projects.projects.length > 0) {
    const result = loadPersistentProject(projects.projects[0].id);
    Logger.log(JSON.stringify(result, null, 2));
    return result;
  }
  return { error: 'هیچ پروژه‌ای وجود ندارد' };
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 v16.0: STATE PERSISTENCE - حفظ و بازیابی وضعیت
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ذخیره وضعیت فعلی پروژه
 */
function saveProjectState(projectId) {
  try {
    const context = loadProjectContext(projectId);
    if (!context) return { success: false, error: 'پروژه یافت نشد' };
    
    const state = {
      savedAt: new Date().toISOString(),
      currentPhase: context.currentPhase,
      lastConversation: context.conversations[context.conversations.length - 1] || null,
      activeModels: context.models.active,
      metrics: context.metrics,
      openFiles: context.files.uploaded.slice(-5),  // آخرین ۵ فایل
      uiState: {
        selectedTab: 'main',
        scrollPosition: 0
      }
    };
    
    // ذخیره در Properties
    const props = PropertiesService.getScriptProperties();
    const stateKey = 'PROJECT_STATE_' + projectId;
    props.setProperty(stateKey, JSON.stringify(state));
    
    // ذخیره در تاریخچه
    const historyKey = 'PROJECT_HISTORY_' + projectId;
    let history = [];
    try {
      history = JSON.parse(props.getProperty(historyKey) || '[]');
    } catch (e) {}
    
    history.push({
      timestamp: state.savedAt,
      phase: context.currentPhase.name,
      action: 'auto_save'
    });
    
    // حفظ فقط ۱۰۰ ورودی آخر
    if (history.length > PERSISTENT_PROJECT_CONFIG.STATE_PERSISTENCE.MAX_HISTORY_ENTRIES) {
      history = history.slice(-PERSISTENT_PROJECT_CONFIG.STATE_PERSISTENCE.MAX_HISTORY_ENTRIES);
    }
    props.setProperty(historyKey, JSON.stringify(history));
    
    Logger.log('✅ وضعیت پروژه ذخیره شد: ' + projectId);
    return { success: true, savedAt: state.savedAt };
    
  } catch (error) {
    Logger.log('❌ خطا در ذخیره وضعیت: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * بازیابی وضعیت پروژه
 */
function restoreProjectState(projectId) {
  try {
    const props = PropertiesService.getScriptProperties();
    const stateKey = 'PROJECT_STATE_' + projectId;
    const stateStr = props.getProperty(stateKey);
    
    if (!stateStr) {
      return { success: false, error: 'وضعیت ذخیره شده‌ای یافت نشد' };
    }
    
    const state = JSON.parse(stateStr);
    
    Logger.log('✅ وضعیت پروژه بازیابی شد: ' + projectId);
    return {
      success: true,
      state: state,
      message: 'وضعیت از ' + new Date(state.savedAt).toLocaleString('fa-IR') + ' بازیابی شد'
    };
    
  } catch (error) {
    Logger.log('❌ خطا در بازیابی وضعیت: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * دریافت تاریخچه پروژه
 */
function getProjectHistory(projectId, limit = 20) {
  try {
    const props = PropertiesService.getScriptProperties();
    const historyKey = 'PROJECT_HISTORY_' + projectId;
    let history = [];
    
    try {
      history = JSON.parse(props.getProperty(historyKey) || '[]');
    } catch (e) {}
    
    return {
      success: true,
      history: history.slice(-limit).reverse(),
      total: history.length
    };
    
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 v16.0: MODEL PERFORMANCE TRACKING - ردیابی عملکرد مدل‌ها
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ثبت امتیاز عملکرد مدل
 */
function recordModelPerformance(projectId, modelId, scores, taskType) {
  try {
    const props = PropertiesService.getScriptProperties();
    const perfKey = 'MODEL_PERF_' + projectId;
    let perfData = {};
    
    try {
      perfData = JSON.parse(props.getProperty(perfKey) || '{}');
    } catch (e) {}
    
    if (!perfData[modelId]) {
      perfData[modelId] = { samples: [], average: 0, history: [] };
    }
    
    // محاسبه امتیاز کل بر اساس وزن‌ها
    const criteria = MODEL_SCORING_SYSTEM.CRITERIA;
    let totalScore = 0;
    for (const [key, config] of Object.entries(criteria)) {
      totalScore += (scores[key.toLowerCase()] || 0) * config.weight;
    }
    
    perfData[modelId].samples.push({
      timestamp: new Date().toISOString(),
      scores: scores,
      totalScore: totalScore,
      taskType: taskType
    });
    
    // حفظ فقط ۵۰ نمونه آخر
    if (perfData[modelId].samples.length > 50) {
      perfData[modelId].samples = perfData[modelId].samples.slice(-50);
    }
    
    // محاسبه میانگین
    const samples = perfData[modelId].samples;
    perfData[modelId].average = samples.reduce((sum, s) => sum + s.totalScore, 0) / samples.length;
    
    // بررسی نیاز به جایگزینی
    const replacement = checkModelReplacement(modelId, perfData[modelId]);
    if (replacement.shouldReplace) {
      perfData[modelId].replacementSuggested = true;
      perfData[modelId].replacementReason = replacement.reason;
      perfData[modelId].suggestedAlternative = replacement.alternative;
    }
    
    props.setProperty(perfKey, JSON.stringify(perfData));
    
    return {
      success: true,
      modelId: modelId,
      totalScore: totalScore,
      average: perfData[modelId].average,
      replacement: replacement
    };
    
  } catch (error) {
    Logger.log('❌ خطا در ثبت عملکرد: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * بررسی نیاز به جایگزینی مدل
 */
function checkModelReplacement(modelId, perfData) {
  const autoReplace = MODEL_SCORING_SYSTEM.AUTO_REPLACEMENT;
  
  // بررسی حداقل نمونه
  if (perfData.samples.length < autoReplace.MIN_SAMPLES) {
    return { shouldReplace: false, reason: 'نمونه کافی نیست' };
  }
  
  // بررسی میانگین
  const thresholds = MODEL_SCORING_SYSTEM.THRESHOLDS;
  if (perfData.average < thresholds.POOR.min) {
    // پیدا کردن جایگزین
    const alternative = findBetterModel(modelId, perfData.samples[0]?.taskType);
    return {
      shouldReplace: true,
      reason: 'میانگین عملکرد زیر حد قابل قبول است',
      alternative: alternative
    };
  }
  
  // بررسی روند کاهشی
  const recent = perfData.samples.slice(-5);
  const earlier = perfData.samples.slice(-10, -5);
  
  if (recent.length >= 5 && earlier.length >= 5) {
    const recentAvg = recent.reduce((s, x) => s + x.totalScore, 0) / recent.length;
    const earlierAvg = earlier.reduce((s, x) => s + x.totalScore, 0) / earlier.length;
    
    const dropPercent = ((earlierAvg - recentAvg) / earlierAvg) * 100;
    
    if (dropPercent >= autoReplace.DROP_THRESHOLD) {
      const alternative = findBetterModel(modelId, perfData.samples[0]?.taskType);
      return {
        shouldReplace: true,
        reason: `کاهش ${dropPercent.toFixed(1)}٪ در عملکرد اخیر`,
        alternative: alternative
      };
    }
  }
  
  return { shouldReplace: false };
}

/**
 * پیدا کردن مدل جایگزین بهتر
 */
function findBetterModel(currentModelId, taskType) {
  const capabilities = MODEL_SCORING_SYSTEM_V16?.MODEL_CAPABILITIES || MODEL_SCORING_SYSTEM.MODEL_CAPABILITIES;
  const currentModel = MODEL_REGISTRY[currentModelId];
  
  if (!currentModel || !capabilities) return null;
  
  // فیلتر مدل‌های همان provider یا provider دیگر
  const candidates = Object.entries(MODEL_REGISTRY)
    .filter(([id, model]) => {
      if (id === currentModelId) return false;
      if (!model.enabled) return false;
      return true;
    })
    .map(([id, model]) => {
      const cap = capabilities[id] || {};
      const score = cap[taskType] || cap.coding || 70;
      return { id, model, score };
    })
    .sort((a, b) => b.score - a.score);
  
  return candidates[0]?.id || null;
}

/**
 * دریافت خلاصه عملکرد مدل‌ها
 */
function getModelsPerformanceSummary(projectId) {
  try {
    const props = PropertiesService.getScriptProperties();
    const perfKey = 'MODEL_PERF_' + projectId;
    let perfData = {};
    
    try {
      perfData = JSON.parse(props.getProperty(perfKey) || '{}');
    } catch (e) {}
    
    const summary = Object.entries(perfData).map(([modelId, data]) => {
      const model = MODEL_REGISTRY[modelId];
      const thresholds = MODEL_SCORING_SYSTEM.THRESHOLDS;
      
      let status = 'unknown';
      if (data.average >= thresholds.EXCELLENT.min) status = 'excellent';
      else if (data.average >= thresholds.GOOD.min) status = 'good';
      else if (data.average >= thresholds.ACCEPTABLE.min) status = 'acceptable';
      else if (data.average >= thresholds.POOR.min) status = 'poor';
      else status = 'replace';
      
      return {
        modelId: modelId,
        name: model?.name || modelId,
        average: Math.round(data.average * 10) / 10,
        samples: data.samples.length,
        status: status,
        statusLabel: thresholds[status.toUpperCase()]?.label || status,
        statusColor: thresholds[status.toUpperCase()]?.color || '#9E9E9E',
        replacementSuggested: data.replacementSuggested || false,
        suggestedAlternative: data.suggestedAlternative
      };
    });
    
    return {
      success: true,
      models: summary,
      lastUpdate: new Date().toISOString()
    };
    
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 v16.0: PROJECT ARCHIVE WITH CONFIRMATION - آرشیو با تأیید
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * درخواست آرشیو پروژه (مرحله ۱)
 */
function requestProjectArchive(projectId) {
  try {
    const props = PropertiesService.getScriptProperties();
    const confirmKey = 'ARCHIVE_CONFIRM_' + projectId;
    
    // ایجاد توکن تأیید
    const confirmToken = Utilities.getUuid();
    const expiresAt = new Date(Date.now() + 5 * 60 * 1000).toISOString(); // ۵ دقیقه
    
    props.setProperty(confirmKey, JSON.stringify({
      token: confirmToken,
      expiresAt: expiresAt,
      step: 1
    }));
    
    return {
      success: true,
      step: 1,
      confirmToken: confirmToken,
      message: 'برای تأیید آرشیو، لطفاً مرحله دوم تأیید را انجام دهید',
      expiresAt: expiresAt
    };
    
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * تأیید نهایی آرشیو پروژه (مرحله ۲)
 */
function confirmProjectArchive(projectId, confirmToken) {
  try {
    const props = PropertiesService.getScriptProperties();
    const confirmKey = 'ARCHIVE_CONFIRM_' + projectId;
    const confirmData = JSON.parse(props.getProperty(confirmKey) || '{}');
    
    // بررسی توکن
    if (!confirmData.token || confirmData.token !== confirmToken) {
      return { success: false, error: 'توکن تأیید نامعتبر است' };
    }
    
    // بررسی انقضا
    if (new Date(confirmData.expiresAt) < new Date()) {
      props.deleteProperty(confirmKey);
      return { success: false, error: 'توکن تأیید منقضی شده است' };
    }
    
    // انجام آرشیو
    const registry = getPersistentProjectRegistry();
    if (registry[projectId]) {
      registry[projectId].status = 'archived';
      registry[projectId].archivedAt = new Date().toISOString();
      savePersistentProjectRegistry(registry);
    }
    
    // پاک کردن توکن
    props.deleteProperty(confirmKey);
    
    Logger.log('✅ پروژه آرشیو شد: ' + projectId);
    
    return {
      success: true,
      message: 'پروژه با موفقیت آرشیو شد',
      archivedAt: registry[projectId].archivedAt
    };
    
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * بازگرداندن پروژه از آرشیو
 */
function restoreProjectFromArchive(projectId) {
  try {
    const registry = getPersistentProjectRegistry();
    
    if (!registry[projectId]) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    if (registry[projectId].status !== 'archived') {
      return { success: false, error: 'پروژه آرشیو نشده است' };
    }
    
    registry[projectId].status = 'active';
    registry[projectId].restoredAt = new Date().toISOString();
    delete registry[projectId].archivedAt;
    
    savePersistentProjectRegistry(registry);
    
    Logger.log('✅ پروژه از آرشیو بازگردانده شد: ' + projectId);
    
    return {
      success: true,
      message: 'پروژه با موفقیت بازگردانده شد'
    };
    
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 END OF PERSISTENT PROJECT MANAGEMENT SYSTEM
// ═══════════════════════════════════════════════════════════════════════════════


// ═══════════════════════════════════════════════════════════════════════════════
// 📌 COMPATIBILITY LAYER - لایه سازگاری با Frontend قدیمی
// ═══════════════════════════════════════════════════════════════════════════════
// این توابع نام‌های قدیمی Frontend را به توابع جدید Persistent Project map می‌کنند

/**
 * لیست پروژه‌های هوشمند (سازگار با Frontend قدیمی)
 */
function getSmartProjectsList() {
  try {
    const result = getPersistentProjects();
    if (!result.success) return result;
    
    // تبدیل فرمت به فرمت قدیمی Frontend
    return {
      success: true,
      projects: result.projects.map(p => ({
        id: p.id,
        name: p.name,
        type: p.type,
        status: p.status || 'active',
        currentStage: p.currentPhaseIndex || 0,
        totalStages: p.totalPhases || 5,
        lastUpdated: p.updatedAt
      }))
    };
  } catch (error) {
    Logger.log('Error in getSmartProjectsList: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * دریافت اطلاعات یک پروژه (سازگار با Frontend قدیمی)
 */
function getSmartProject(projectId) {
  try {
    const result = loadPersistentProject(projectId);
    if (!result.success) return result;
    
    const context = result.context;
    
    // ✅ v17.1.5: بازگرداندن فازها با اطلاعات کامل
    const phases = (context.phases || []).map((phase, index) => ({
      id: phase.id,
      name: phase.name,
      description: phase.description,
      status: phase.status,
      progress: phase.progress || 0,
      startedAt: phase.startedAt,
      completedAt: phase.completedAt,
      notes: phase.notes
    }));
    
    // تبدیل فازها به مراحل (برای سازگاری با UI قدیمی)
    const stages = phases;
    
    // پیدا کردن مرحله فعلی
    const currentStageIndex = stages.findIndex(s => s.status === 'in_progress');
    
    // ✅ v17.1.5: بازگرداندن roadmap کامل
    const roadmap = context.roadmap || { tasks: [] };
    
    // پاکسازی وابستگی‌های نادرست از تسک‌های خودکار
    if (roadmap.tasks) {
      roadmap.tasks = roadmap.tasks.map(task => {
        if (task.autoCreated) {
          return { ...task, dependencies: [] };
        }
        return task;
      });
    }
    
    return {
      success: true,
      project: {
        id: projectId,
        name: context.project.name,
        type: context.project.type,
        description: context.project.description,
        goal: context.project.goal,
        status: context.project.status,
        createdAt: context.project.createdAt,
        lastUpdated: context.lastUpdated || context.project.lastUpdated,
        // ✅ v17.1.5: هم phases و هم stages
        phases: phases,
        stages: stages,
        currentStageIndex: currentStageIndex >= 0 ? currentStageIndex : 0,
        // ✅ v17.1.5: roadmap کامل
        roadmap: roadmap,
        // ✅ v17.1.5: مدل‌ها با اطلاعات بیشتر
        models: context.models.active || [],
        modelScores: context.models.scores || {},
        primaryModel: context.models.primary,
        modelHistory: context.models.history || [],
        // ✅ v17.1.5: همه مکالمات (نه فقط 10 تا)
        conversations: context.conversations || [],
        // ✅ v17.1.5: تایم‌لاین و سایر داده‌ها
        timeline: context.timeline || [],
        files: context.files || [],
        metrics: context.metrics || {},
        currentPhase: context.currentPhase
      },
      urls: {
        folder: result.folderUrl,
        sheet: result.sheetUrl
      }
    };
  } catch (error) {
    Logger.log('Error in getSmartProject: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * ایجاد پروژه جدید (سازگار با Frontend قدیمی)
 * @param {string} name - نام پروژه
 * @param {string} type - نوع پروژه (CODING, LEARNING, RESEARCH, CREATIVE, BUSINESS, CUSTOM)
 * @param {string} description - توضیحات
 * @param {Array} customStages - مراحل سفارشی (برای نوع CUSTOM)
 */
function createSmartProject(name, type, description, customStages) {
  try {
    // تبدیل نوع از حروف بزرگ به کوچک
    const typeMap = {
      'CODING': 'coding',
      'LEARNING': 'learning',
      'RESEARCH': 'research',
      'CREATIVE': 'writing',
      'BUSINESS': 'analysis',
      'CUSTOM': 'custom'
    };
    
    const mappedType = typeMap[type] || type.toLowerCase() || 'coding';
    
    // ✅ v17.1.4: انتخاب داینامیک مدل‌ها بر اساس نوع پروژه
    const enabledModels = getEnabledModels() || [];
    let projectModels = [];
    
    // انتخاب مدل‌های مناسب بر اساس نوع پروژه
    if (enabledModels.length > 0) {
      // اولویت‌بندی مدل‌ها بر اساس نوع پروژه
      const typeModelPriority = {
        'coding': ['gpt-4-turbo', 'claude-sonnet-4-20250514', 'gemini-2.5-pro'],
        'writing': ['claude-sonnet-4-20250514', 'gpt-4-turbo', 'gemini-2.5-pro'],
        'analysis': ['gpt-4-turbo', 'claude-sonnet-4-20250514', 'gemini-2.5-pro'],
        'research': ['gemini-2.5-pro', 'gpt-4-turbo', 'claude-sonnet-4-20250514']
      };
      
      const priorityList = typeModelPriority[mappedType] || typeModelPriority['coding'];
      
      // اضافه کردن مدل‌های فعال به ترتیب اولویت
      for (const modelId of priorityList) {
        if (enabledModels.some(m => m.id === modelId || m.modelId === modelId)) {
          projectModels.push(modelId);
        }
      }
      
      // اگر هنوز مدلی نداریم، همه مدل‌های فعال رو اضافه کن
      if (projectModels.length === 0) {
        projectModels = enabledModels.slice(0, 3).map(m => m.id || m.modelId);
      }
    }
    
    // اگر هیچ مدلی پیدا نشد، fallback به پیش‌فرض
    if (projectModels.length === 0) {
      projectModels = ['gpt-4-turbo', 'claude-sonnet-4-20250514'];
    }
    
    // تبدیل فرمت قدیمی به جدید
    const newProjectData = {
      name: name,
      type: mappedType,
      description: description || '',
      goal: description || '',
      complexity: 'intermediate',
      models: projectModels,
      activeModel: projectModels[0] // مدل اول به عنوان فعال
    };
    
    // اگر مراحل سفارشی داده شده، آنها را اضافه کن
    if (customStages && Array.isArray(customStages) && customStages.length > 0) {
      newProjectData.customPhases = customStages.map((stage, index) => ({
        id: 'phase_custom_' + (index + 1),
        name: stage,
        description: stage,
        status: index === 0 ? 'in_progress' : 'pending',
        steps: [],
        progress: 0
      }));
    }
    
    return createPersistentProject(newProjectData);
  } catch (error) {
    Logger.log('Error in createSmartProject: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * ارسال پیام به پروژه (سازگار با Frontend قدیمی)
 */
function sendSmartProjectPrompt(projectId, message, targetModel) {
  try {
    const options = {};
    if (targetModel) {
      options.model = targetModel;
    } else {
      options.autoSelect = true;
    }
    
    const result = sendPersistentProjectMessage(projectId, message, options);
    
    // اطمینان از وجود response
    if (result.success && !result.response) {
      result.response = 'پاسخی دریافت نشد';
    }
    
    return result;
  } catch (error) {
    Logger.log('Error in sendSmartProjectPrompt: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * امتیازدهی به مدل (سازگار با Frontend قدیمی)
 * @param {string} projectId - شناسه پروژه
 * @param {string} modelId - شناسه مدل
 * @param {number|object} scores - امتیاز (عدد 0-100 یا object با معیارها)
 * @param {string} scoreType - نوع امتیازدهی (general, accuracy, etc.)
 * @param {string} comment - توضیحات
 */
function scoreSmartProjectModel(projectId, modelId, scores, scoreType, comment) {
  try {
    // اگر scores یک عدد ساده باشد، تبدیل به فرمت کامل
    if (typeof scores === 'number') {
      const simpleScore = Math.min(100, Math.max(0, scores));
      scores = {
        accuracy: simpleScore,
        completeness: simpleScore,
        speed: simpleScore,
        relevance: simpleScore,
        creativity: simpleScore
      };
    }
    
    return apiScoreResponse(projectId, null, modelId, scores);
  } catch (error) {
    Logger.log('Error in scoreSmartProjectModel: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * تغییر مدل پروژه (سازگار با Frontend قدیمی)
 */
/**
 * ✅ v17.1.4: تغییر مدل پروژه هوشمند
 */
function changeSmartProjectModel(projectId, newModelId, reason) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    const oldModelId = context.activeModel || 'unknown';
    
    // ثبت تغییر در تاریخچه
    if (!context.modelHistory) {
      context.modelHistory = [];
    }
    context.modelHistory.push({
      from: oldModelId,
      to: newModelId,
      reason: reason || 'تغییر دستی',
      timestamp: new Date().toISOString()
    });
    
    // به‌روزرسانی مدل فعال
    context.activeModel = newModelId;
    
    // اضافه کردن به تایم‌لاین
    if (!context.timeline) {
      context.timeline = [];
    }
    context.timeline.push({
      type: 'MODEL_CHANGED',
      message: `مدل از ${oldModelId} به ${newModelId} تغییر کرد`,
      timestamp: new Date().toISOString()
    });
    
    // ذخیره
    saveSmartProjectContext(projectId, context);
    
    Logger.log(`✅ مدل پروژه ${projectId} به ${newModelId} تغییر کرد`);
    
    return { success: true, activeModel: newModelId };
    
  } catch (error) {
    Logger.log('Error in changeSmartProjectModel: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * تکمیل مرحله (سازگار با Frontend قدیمی)
 */
function completeSmartStage(projectId) {
  try {
    return apiNextPhase(projectId);
  } catch (error) {
    Logger.log('Error in completeSmartStage: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * برگشت به مرحله قبل (سازگار با Frontend قدیمی)
 */
function rollbackSmartStage(projectId) {
  try {
    return apiRollbackPhase(projectId);
  } catch (error) {
    Logger.log('Error in rollbackSmartStage: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * دریافت فایل‌های پروژه (سازگار با Frontend قدیمی)
 */
function getSmartProjectFiles(projectId) {
  try {
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    if (!projectInfo) return { success: false, error: 'پروژه یافت نشد' };
    
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    // ترکیب فایل‌های آپلود شده و تولید شده
    const allFiles = [];
    
    // فایل‌های آپلود شده
    if (context.files && context.files.uploaded) {
      context.files.uploaded.forEach(f => {
        allFiles.push({
          id: f.id,
          name: f.name,
          url: f.url,
          category: 'آپلود شده',
          type: f.mimeType || 'unknown',
          size: f.size,
          date: f.uploadedAt
        });
      });
    }
    
    // فایل‌های تولید شده
    if (context.files && context.files.generated) {
      context.files.generated.forEach(f => {
        allFiles.push({
          id: f.id,
          name: f.name,
          url: f.url,
          category: f.category || 'تولید شده',
          type: f.type || 'unknown',
          size: f.size,
          date: f.createdAt
        });
      });
    }
    
    // ساختار فولدری
    const folder = DriveApp.getFolderById(projectInfo.folderId);
    const structure = getPersistentFolderStructure(folder);
    
    return { 
      success: true, 
      files: allFiles,
      structure: structure,
      folderUrl: folder.getUrl() 
    };
  } catch (error) {
    Logger.log('Error in getSmartProjectFiles: ' + error);
    return { success: false, error: error.message, files: [] };
  }
}

/**
 * انتخاب هوشمند مدل برای پروژه
 */
function smartSelectProjectModel(projectId) {
  try {
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    if (!projectInfo) return { success: false, error: 'پروژه یافت نشد' };
    
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    const bestModel = selectBestPersistentModel(context);
    
    return {
      success: true,
      model: bestModel,
      availableModels: context.models.active,
      scores: context.models.scores
    };
  } catch (error) {
    Logger.log('Error in smartSelectProjectModel: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * تحلیل لاگ‌های پروژه
 */
function analyzeSmartProjectLog(projectId, logContent) {
  try {
    // ذخیره لاگ در پروژه
    const saveResult = apiSaveLog(projectId, logContent, 'user_log');
    
    // تحلیل ساده لاگ
    const analysis = {
      totalLines: logContent.split('\n').length,
      hasErrors: /error|exception|failed/i.test(logContent),
      hasWarnings: /warning|warn/i.test(logContent),
      errorCount: (logContent.match(/error/gi) || []).length,
      warningCount: (logContent.match(/warning/gi) || []).length
    };
    
    return {
      success: true,
      saved: saveResult.success,
      analysis: analysis
    };
  } catch (error) {
    Logger.log('Error in analyzeSmartProjectLog: ' + error);
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 END OF COMPATIBILITY LAYER
// ═══════════════════════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 MODEL ARCHIVE SYSTEM - سیستم آرشیو مدل‌های غیرفعال
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * دریافت لیست مدل‌های آرشیو شده
 */
function getArchivedModels() {
  const props = PropertiesService.getScriptProperties();
  const archived = props.getProperty('ARCHIVED_MODELS');
  return archived ? JSON.parse(archived) : {};
}

/**
 * ذخیره لیست مدل‌های آرشیو شده
 */
function saveArchivedModels(archived) {
  const props = PropertiesService.getScriptProperties();
  props.setProperty('ARCHIVED_MODELS', JSON.stringify(archived));
}

/**
 * آرشیو کردن یک مدل
 * @param {string} modelId - شناسه مدل
 * @param {string} reason - دلیل آرشیو
 * @param {boolean} autoArchived - آیا خودکار آرشیو شده
 */
function archiveModel(modelId, reason, autoArchived = false) {
  try {
    const archived = getArchivedModels();
    
    archived[modelId] = {
      archivedAt: new Date().toISOString(),
      reason: reason || 'آرشیو دستی',
      autoArchived: autoArchived,
      errorCount: archived[modelId]?.errorCount || 0,
      lastError: archived[modelId]?.lastError || null
    };
    
    saveArchivedModels(archived);
    
    // غیرفعال کردن در MODEL_REGISTRY
    if (MODEL_REGISTRY[modelId]) {
      MODEL_REGISTRY[modelId].enabled = false;
      MODEL_REGISTRY[modelId].archived = true;
    }
    
    Logger.log('📦 مدل آرشیو شد: ' + modelId + ' - دلیل: ' + reason);
    
    return { success: true, modelId: modelId, message: 'مدل با موفقیت آرشیو شد' };
  } catch (error) {
    Logger.log('❌ خطا در آرشیو مدل: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * فعال‌سازی مجدد مدل آرشیو شده
 */
function unarchiveModel(modelId) {
  try {
    const archived = getArchivedModels();
    
    if (archived[modelId]) {
      delete archived[modelId];
      saveArchivedModels(archived);
    }
    
    // فعال کردن در MODEL_REGISTRY
    if (MODEL_REGISTRY[modelId]) {
      MODEL_REGISTRY[modelId].enabled = true;
      MODEL_REGISTRY[modelId].archived = false;
    }
    
    Logger.log('✅ مدل از آرشیو خارج شد: ' + modelId);
    
    return { success: true, modelId: modelId, message: 'مدل با موفقیت فعال شد' };
  } catch (error) {
    Logger.log('❌ خطا در فعال‌سازی مدل: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * ثبت خطای مدل (برای آرشیو خودکار)
 */
function recordModelError(modelId, errorMessage) {
  const archived = getArchivedModels();
  const errorThreshold = 5; // تعداد خطا برای آرشیو خودکار
  
  if (!archived[modelId]) {
    archived[modelId] = { errorCount: 0, errors: [] };
  }
  
  archived[modelId].errorCount = (archived[modelId].errorCount || 0) + 1;
  archived[modelId].lastError = {
    message: errorMessage,
    timestamp: new Date().toISOString()
  };
  archived[modelId].errors = archived[modelId].errors || [];
  archived[modelId].errors.push({
    message: errorMessage,
    timestamp: new Date().toISOString()
  });
  
  // فقط 10 خطای آخر را نگه دار
  if (archived[modelId].errors.length > 10) {
    archived[modelId].errors = archived[modelId].errors.slice(-10);
  }
  
  saveArchivedModels(archived);
  
  // اگر تعداد خطاها از حد مجاز بیشتر شد، خودکار آرشیو کن
  if (archived[modelId].errorCount >= errorThreshold && !archived[modelId].archivedAt) {
    Logger.log('⚠️ آرشیو خودکار مدل به دلیل خطاهای مکرر: ' + modelId);
    archiveModel(modelId, 'آرشیو خودکار به دلیل ' + errorThreshold + ' خطای متوالی', true);
    return { archived: true, modelId: modelId };
  }
  
  return { archived: false, errorCount: archived[modelId].errorCount };
}

/**
 * پاک کردن خطاهای یک مدل
 */
function clearModelErrors(modelId) {
  const archived = getArchivedModels();
  
  if (archived[modelId]) {
    archived[modelId].errorCount = 0;
    archived[modelId].errors = [];
    archived[modelId].lastError = null;
    saveArchivedModels(archived);
  }
  
  return { success: true };
}

/**
 * دریافت لیست مدل‌های فعال (بدون آرشیو شده‌ها)
 */
function getActiveModels() {
  const archived = getArchivedModels();
  const activeModels = {};
  
  for (const [modelId, model] of Object.entries(MODEL_REGISTRY)) {
    if (!archived[modelId]?.archivedAt && model.enabled !== false) {
      activeModels[modelId] = model;
    }
  }
  
  return activeModels;
}

/**
 * بررسی وضعیت مدل
 */
function getModelStatus(modelId) {
  const archived = getArchivedModels();
  const modelInfo = MODEL_REGISTRY[modelId];
  
  return {
    modelId: modelId,
    exists: !!modelInfo,
    enabled: modelInfo?.enabled !== false,
    archived: !!archived[modelId]?.archivedAt,
    errorCount: archived[modelId]?.errorCount || 0,
    lastError: archived[modelId]?.lastError,
    archivedAt: archived[modelId]?.archivedAt,
    archiveReason: archived[modelId]?.reason
  };
}

/**
 * دریافت گزارش کامل مدل‌ها
 */
function getModelsReport() {
  const archived = getArchivedModels();
  const report = {
    total: Object.keys(MODEL_REGISTRY).length,
    active: 0,
    archived: 0,
    withErrors: 0,
    models: []
  };
  
  for (const [modelId, model] of Object.entries(MODEL_REGISTRY)) {
    const status = getModelStatus(modelId);
    
    if (status.archived) report.archived++;
    else if (status.enabled) report.active++;
    if (status.errorCount > 0) report.withErrors++;
    
    report.models.push({
      id: modelId,
      name: model.name,
      provider: model.provider,
      ...status
    });
  }
  
  return report;
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 EXTENDED FILE FORMAT SUPPORT - پشتیبانی از فرمت‌های بیشتر
// ═══════════════════════════════════════════════════════════════════════════════

const EXTENDED_FILE_FORMATS = {
  // کد
  'gs': { category: 'code', mimeType: 'application/javascript', icon: '📜', processor: 'code' },
  'js': { category: 'code', mimeType: 'application/javascript', icon: '📜', processor: 'code' },
  'ts': { category: 'code', mimeType: 'application/typescript', icon: '📜', processor: 'code' },
  'jsx': { category: 'code', mimeType: 'text/jsx', icon: '⚛️', processor: 'code' },
  'tsx': { category: 'code', mimeType: 'text/tsx', icon: '⚛️', processor: 'code' },
  'py': { category: 'code', mimeType: 'text/x-python', icon: '🐍', processor: 'code' },
  'java': { category: 'code', mimeType: 'text/x-java', icon: '☕', processor: 'code' },
  'cpp': { category: 'code', mimeType: 'text/x-c++', icon: '⚙️', processor: 'code' },
  'c': { category: 'code', mimeType: 'text/x-c', icon: '⚙️', processor: 'code' },
  'h': { category: 'code', mimeType: 'text/x-c', icon: '⚙️', processor: 'code' },
  'cs': { category: 'code', mimeType: 'text/x-csharp', icon: '#️⃣', processor: 'code' },
  'go': { category: 'code', mimeType: 'text/x-go', icon: '🐹', processor: 'code' },
  'rs': { category: 'code', mimeType: 'text/x-rust', icon: '🦀', processor: 'code' },
  'rb': { category: 'code', mimeType: 'text/x-ruby', icon: '💎', processor: 'code' },
  'php': { category: 'code', mimeType: 'text/x-php', icon: '🐘', processor: 'code' },
  'swift': { category: 'code', mimeType: 'text/x-swift', icon: '🍎', processor: 'code' },
  'kt': { category: 'code', mimeType: 'text/x-kotlin', icon: 'K', processor: 'code' },
  'scala': { category: 'code', mimeType: 'text/x-scala', icon: 'S', processor: 'code' },
  'sh': { category: 'code', mimeType: 'text/x-shellscript', icon: '🐚', processor: 'code' },
  'bash': { category: 'code', mimeType: 'text/x-shellscript', icon: '🐚', processor: 'code' },
  'ps1': { category: 'code', mimeType: 'text/x-powershell', icon: '💠', processor: 'code' },
  'sql': { category: 'code', mimeType: 'text/x-sql', icon: '🗃️', processor: 'code' },
  'r': { category: 'code', mimeType: 'text/x-r', icon: '📊', processor: 'code' },
  'matlab': { category: 'code', mimeType: 'text/x-matlab', icon: '📐', processor: 'code' },
  'mq4': { category: 'code', mimeType: 'text/plain', icon: '📈', processor: 'code' },
  'mq5': { category: 'code', mimeType: 'text/plain', icon: '📈', processor: 'code' },
  'ex4': { category: 'binary', mimeType: 'application/octet-stream', icon: '📈', processor: 'binary' },
  'ex5': { category: 'binary', mimeType: 'application/octet-stream', icon: '📈', processor: 'binary' },
  
  // وب
  'html': { category: 'web', mimeType: 'text/html', icon: '🌐', processor: 'code' },
  'htm': { category: 'web', mimeType: 'text/html', icon: '🌐', processor: 'code' },
  'css': { category: 'web', mimeType: 'text/css', icon: '🎨', processor: 'code' },
  'scss': { category: 'web', mimeType: 'text/x-scss', icon: '🎨', processor: 'code' },
  'sass': { category: 'web', mimeType: 'text/x-sass', icon: '🎨', processor: 'code' },
  'less': { category: 'web', mimeType: 'text/x-less', icon: '🎨', processor: 'code' },
  'vue': { category: 'web', mimeType: 'text/x-vue', icon: '💚', processor: 'code' },
  'svelte': { category: 'web', mimeType: 'text/x-svelte', icon: '🧡', processor: 'code' },
  
  // داده
  'json': { category: 'data', mimeType: 'application/json', icon: '📋', processor: 'data' },
  'xml': { category: 'data', mimeType: 'application/xml', icon: '📋', processor: 'data' },
  'yaml': { category: 'data', mimeType: 'text/yaml', icon: '📋', processor: 'data' },
  'yml': { category: 'data', mimeType: 'text/yaml', icon: '📋', processor: 'data' },
  'toml': { category: 'data', mimeType: 'text/toml', icon: '📋', processor: 'data' },
  'csv': { category: 'data', mimeType: 'text/csv', icon: '📊', processor: 'data' },
  'tsv': { category: 'data', mimeType: 'text/tab-separated-values', icon: '📊', processor: 'data' },
  
  // متن
  'txt': { category: 'text', mimeType: 'text/plain', icon: '📄', processor: 'text' },
  'md': { category: 'text', mimeType: 'text/markdown', icon: '📝', processor: 'text' },
  'markdown': { category: 'text', mimeType: 'text/markdown', icon: '📝', processor: 'text' },
  'rst': { category: 'text', mimeType: 'text/x-rst', icon: '📝', processor: 'text' },
  'log': { category: 'text', mimeType: 'text/plain', icon: '📋', processor: 'log' },
  
  // تنظیمات
  'env': { category: 'config', mimeType: 'text/plain', icon: '⚙️', processor: 'config' },
  'ini': { category: 'config', mimeType: 'text/plain', icon: '⚙️', processor: 'config' },
  'conf': { category: 'config', mimeType: 'text/plain', icon: '⚙️', processor: 'config' },
  'config': { category: 'config', mimeType: 'text/plain', icon: '⚙️', processor: 'config' },
  'properties': { category: 'config', mimeType: 'text/plain', icon: '⚙️', processor: 'config' },
  
  // سند
  'pdf': { category: 'document', mimeType: 'application/pdf', icon: '📕', processor: 'document' },
  'doc': { category: 'document', mimeType: 'application/msword', icon: '📘', processor: 'document' },
  'docx': { category: 'document', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', icon: '📘', processor: 'document' },
  'xls': { category: 'document', mimeType: 'application/vnd.ms-excel', icon: '📗', processor: 'spreadsheet' },
  'xlsx': { category: 'document', mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', icon: '📗', processor: 'spreadsheet' },
  'ppt': { category: 'document', mimeType: 'application/vnd.ms-powerpoint', icon: '📙', processor: 'presentation' },
  'pptx': { category: 'document', mimeType: 'application/vnd.openxmlformats-officedocument.presentationml.presentation', icon: '📙', processor: 'presentation' },
  
  // آرشیو
  'zip': { category: 'archive', mimeType: 'application/zip', icon: '📦', processor: 'archive' },
  'rar': { category: 'archive', mimeType: 'application/x-rar-compressed', icon: '📦', processor: 'archive' },
  '7z': { category: 'archive', mimeType: 'application/x-7z-compressed', icon: '📦', processor: 'archive' },
  'tar': { category: 'archive', mimeType: 'application/x-tar', icon: '📦', processor: 'archive' },
  'gz': { category: 'archive', mimeType: 'application/gzip', icon: '📦', processor: 'archive' },
  
  // تصویر
  'png': { category: 'image', mimeType: 'image/png', icon: '🖼️', processor: 'image' },
  'jpg': { category: 'image', mimeType: 'image/jpeg', icon: '🖼️', processor: 'image' },
  'jpeg': { category: 'image', mimeType: 'image/jpeg', icon: '🖼️', processor: 'image' },
  'gif': { category: 'image', mimeType: 'image/gif', icon: '🖼️', processor: 'image' },
  'webp': { category: 'image', mimeType: 'image/webp', icon: '🖼️', processor: 'image' },
  'svg': { category: 'image', mimeType: 'image/svg+xml', icon: '🎨', processor: 'image' },
  'ico': { category: 'image', mimeType: 'image/x-icon', icon: '🖼️', processor: 'image' }
};

/**
 * دریافت اطلاعات فرمت فایل
 */
function getFileFormatInfo(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  return EXTENDED_FILE_FORMATS[ext] || { 
    category: 'other', 
    mimeType: 'application/octet-stream', 
    icon: '📄', 
    processor: 'generic' 
  };
}

/**
 * بررسی پشتیبانی از فرمت فایل
 */
function isFileFormatSupported(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  return !!EXTENDED_FILE_FORMATS[ext];
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 ZIP FILE PROCESSING - پردازش فایل‌های فشرده
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * استخراج و پردازش فایل ZIP
 * @param {string} fileId - شناسه فایل ZIP در Drive
 * @param {string} projectId - شناسه پروژه (اختیاری)
 */
function processZipFile(fileId, projectId) {
  try {
    Logger.log('📦 شروع پردازش فایل ZIP: ' + fileId);
    
    const file = DriveApp.getFileById(fileId);
    const blob = file.getBlob();
    const zipContent = Utilities.unzip(blob);
    
    const results = {
      success: true,
      totalFiles: zipContent.length,
      processed: [],
      errors: []
    };
    
    for (const item of zipContent) {
      try {
        const fileName = item.getName();
        const content = item.getDataAsString();
        const formatInfo = getFileFormatInfo(fileName);
        
        results.processed.push({
          name: fileName,
          category: formatInfo.category,
          processor: formatInfo.processor,
          size: content.length,
          icon: formatInfo.icon
        });
        
        // اگر پروژه مشخص شده، فایل را در پروژه ذخیره کن
        if (projectId) {
          const registry = getPersistentProjectRegistry();
          const projectInfo = registry[projectId];
          if (projectInfo) {
            const projectFolder = DriveApp.getFolderById(projectInfo.folderId);
            const uploadsFolder = getOrCreatePersistentFolder(projectFolder, '01_Uploads');
            uploadsFolder.createFile(item);
          }
        }
        
      } catch (itemError) {
        results.errors.push({
          name: item.getName(),
          error: itemError.message
        });
      }
    }
    
    Logger.log('✅ پردازش ZIP تکمیل شد: ' + results.totalFiles + ' فایل');
    return results;
    
  } catch (error) {
    Logger.log('❌ خطا در پردازش ZIP: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * تحلیل محتوای فایل ZIP بدون استخراج
 */
function analyzeZipFile(fileId) {
  try {
    const file = DriveApp.getFileById(fileId);
    const blob = file.getBlob();
    const zipContent = Utilities.unzip(blob);
    
    const analysis = {
      totalFiles: zipContent.length,
      totalSize: 0,
      categories: {},
      files: []
    };
    
    for (const item of zipContent) {
      const fileName = item.getName();
      const formatInfo = getFileFormatInfo(fileName);
      const size = item.getBytes().length;
      
      analysis.totalSize += size;
      
      if (!analysis.categories[formatInfo.category]) {
        analysis.categories[formatInfo.category] = { count: 0, size: 0 };
      }
      analysis.categories[formatInfo.category].count++;
      analysis.categories[formatInfo.category].size += size;
      
      analysis.files.push({
        name: fileName,
        category: formatInfo.category,
        icon: formatInfo.icon,
        size: size
      });
    }
    
    return { success: true, analysis: analysis };
    
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 JOURNAL SYSTEM - سیستم ژورنال و ثبت اقدامات
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * دریافت ژورنال
 */
function getJournal() {
  const props = PropertiesService.getScriptProperties();
  const journal = props.getProperty('SYSTEM_JOURNAL');
  return journal ? JSON.parse(journal) : [];
}

/**
 * ذخیره ژورنال
 */
function saveJournal(journal) {
  const props = PropertiesService.getScriptProperties();
  // فقط 1000 رکورد آخر را نگه دار
  if (journal.length > 1000) {
    journal = journal.slice(-1000);
  }
  props.setProperty('SYSTEM_JOURNAL', JSON.stringify(journal));
}

/**
 * ثبت رویداد در ژورنال
 * @param {string} action - نوع اقدام
 * @param {string} category - دسته‌بندی (project, model, file, system, error)
 * @param {object} details - جزئیات
 * @param {string} projectId - شناسه پروژه (اختیاری)
 */
function logToJournal(action, category, details, projectId = null) {
  try {
    const journal = getJournal();
    
    const entry = {
      id: 'j_' + Date.now(),
      timestamp: new Date().toISOString(),
      action: action,
      category: category,
      projectId: projectId,
      details: details,
      user: Session.getActiveUser().getEmail() || 'unknown'
    };
    
    journal.push(entry);
    saveJournal(journal);
    
    Logger.log(`📔 Journal: [${category}] ${action}`);
    
    return entry;
  } catch (error) {
    Logger.log('خطا در ثبت ژورنال: ' + error);
    return null;
  }
}

/**
 * دریافت ژورنال با فیلتر
 */
function getFilteredJournal(options = {}) {
  const journal = getJournal();
  let filtered = journal;
  
  if (options.category) {
    filtered = filtered.filter(e => e.category === options.category);
  }
  
  if (options.projectId) {
    filtered = filtered.filter(e => e.projectId === options.projectId);
  }
  
  if (options.action) {
    filtered = filtered.filter(e => e.action.includes(options.action));
  }
  
  if (options.fromDate) {
    filtered = filtered.filter(e => new Date(e.timestamp) >= new Date(options.fromDate));
  }
  
  if (options.toDate) {
    filtered = filtered.filter(e => new Date(e.timestamp) <= new Date(options.toDate));
  }
  
  // مرتب‌سازی از جدید به قدیم
  filtered.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  
  // صفحه‌بندی
  const page = options.page || 1;
  const perPage = options.perPage || 50;
  const start = (page - 1) * perPage;
  
  return {
    entries: filtered.slice(start, start + perPage),
    total: filtered.length,
    page: page,
    totalPages: Math.ceil(filtered.length / perPage)
  };
}

/**
 * پاک کردن ژورنال
 */
function clearJournal(olderThanDays = 30) {
  const journal = getJournal();
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - olderThanDays);
  
  const filtered = journal.filter(e => new Date(e.timestamp) >= cutoffDate);
  const removed = journal.length - filtered.length;
  
  saveJournal(filtered);
  
  return { success: true, removed: removed, remaining: filtered.length };
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SMART PROJECT INITIALIZATION - شروع هوشمند پروژه
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * تحلیل هوشمند درخواست و ایجاد پروژه خودکار
 * @param {string} userPrompt - درخواست یا توضیحات کاربر
 * @param {Array} attachments - فایل‌های پیوست
 */
function smartCreateProject(userPrompt, attachments = []) {
  try {
    Logger.log('🧠 شروع تحلیل هوشمند برای ایجاد پروژه...');
    
    logToJournal('smart_project_init', 'project', { prompt: userPrompt.substring(0, 200) });
    
    // ساخت پرامپت تحلیل
    const analysisPrompt = `لطفاً درخواست زیر را تحلیل کن و اطلاعات پروژه را استخراج کن:

درخواست کاربر:
${userPrompt}

${attachments.length > 0 ? `فایل‌های پیوست: ${attachments.map(a => a.name).join(', ')}` : ''}

لطفاً پاسخ را به صورت JSON با فرمت زیر بده:
{
  "projectName": "نام پیشنهادی پروژه",
  "projectType": "coding|learning|research|writing|design|analysis|custom",
  "description": "توضیح کوتاه پروژه",
  "goal": "هدف اصلی",
  "complexity": "beginner|intermediate|advanced|expert",
  "phases": [
    {"name": "نام فاز", "description": "توضیح", "estimatedDuration": "مدت تخمینی"}
  ],
  "suggestedModels": ["model1", "model2"],
  "requirements": ["نیازمندی 1", "نیازمندی 2"],
  "keywords": ["کلمه کلیدی 1", "کلمه کلیدی 2"]
}`;

    // استفاده از یک مدل قوی برای تحلیل
    const analysisModel = 'gpt-4-turbo';
    const analysisResponse = callModel(analysisModel, analysisPrompt, []);
    
    // استخراج JSON از پاسخ
    let projectInfo;
    try {
      const jsonMatch = analysisResponse.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        projectInfo = JSON.parse(jsonMatch[0]);
      } else {
        throw new Error('JSON یافت نشد');
      }
    } catch (parseError) {
      Logger.log('⚠️ خطا در parse پاسخ، استفاده از مقادیر پیش‌فرض');
      projectInfo = {
        projectName: 'پروژه جدید ' + new Date().toLocaleDateString('fa-IR'),
        projectType: 'custom',
        description: userPrompt.substring(0, 500),
        goal: userPrompt.substring(0, 200),
        complexity: 'intermediate',
        phases: [],
        suggestedModels: ['gpt-4-turbo', 'claude-sonnet-4-20250514']
      };
    }
    
    // ایجاد پروژه
    const createResult = createPersistentProject({
      name: projectInfo.projectName,
      type: projectInfo.projectType,
      description: projectInfo.description,
      goal: projectInfo.goal,
      complexity: projectInfo.complexity,
      models: projectInfo.suggestedModels || ['gpt-4-turbo', 'claude-sonnet-4-20250514'],
      customPhases: projectInfo.phases
    });
    
    if (!createResult.success) {
      return createResult;
    }
    
    // پردازش فایل‌های پیوست
    if (attachments.length > 0) {
      for (const attachment of attachments) {
        apiUploadToProject(createResult.projectId, attachment.name, attachment.content, attachment.mimeType);
      }
    }
    
    // ثبت در ژورنال
    logToJournal('project_created', 'project', {
      projectId: createResult.projectId,
      name: projectInfo.projectName,
      type: projectInfo.projectType,
      smartCreated: true
    }, createResult.projectId);
    
    return {
      success: true,
      projectId: createResult.projectId,
      projectInfo: projectInfo,
      folderUrl: createResult.folderUrl,
      sheetUrl: createResult.sheetUrl,
      message: 'پروژه با موفقیت به صورت هوشمند ایجاد شد'
    };
    
  } catch (error) {
    Logger.log('❌ خطا در ایجاد هوشمند پروژه: ' + error);
    logToJournal('smart_project_error', 'error', { error: error.message });
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 AUTOMATIC PHASE MANAGEMENT - مدیریت خودکار فازها
// ═══════════════════════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════════════════════
// ✅ v16.0: PHASE 4 - INTELLIGENT PROCESS AUTOMATION
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v16.0: تنظیمات هوشمندسازی فرآیندها
 */
const INTELLIGENT_CONFIG = {
  // الگوهای پیشرفته تحلیل لاگ
  PATTERNS: {
    SUCCESS: [
      { pattern: /success(?:ful(?:ly)?)?/gi, weight: 2, label: 'موفقیت' },
      { pattern: /completed?/gi, weight: 2, label: 'تکمیل' },
      { pattern: /passed/gi, weight: 2, label: 'قبول' },
      { pattern: /✓|✅|👍|🎉|✔️/g, weight: 3, label: 'ایموجی موفقیت' },
      { pattern: /done|finished|ready/gi, weight: 1.5, label: 'پایان' },
      { pattern: /build succeeded|compilation successful/gi, weight: 3, label: 'بیلد موفق' },
      { pattern: /tests? passed|all tests? (passed|green)/gi, weight: 3, label: 'تست موفق' },
      { pattern: /deployed (successfully|to production)/gi, weight: 3, label: 'دیپلوی موفق' },
      { pattern: /no errors? (found|detected)/gi, weight: 2, label: 'بدون خطا' },
      { pattern: /merge(?:d)? successfully/gi, weight: 2, label: 'مرج موفق' },
      { pattern: /installation complete/gi, weight: 2, label: 'نصب کامل' }
    ],
    ERROR: [
      { pattern: /error(?:s)?:/gi, weight: 2, label: 'خطا', category: 'generic' },
      { pattern: /failed|failure/gi, weight: 2, label: 'شکست', category: 'generic' },
      { pattern: /exception|thrown/gi, weight: 2.5, label: 'استثنا', category: 'runtime' },
      { pattern: /✗|❌|👎|💥|🔥/g, weight: 3, label: 'ایموجی خطا', category: 'generic' },
      { pattern: /crash(?:ed)?|segfault/gi, weight: 3, label: 'کرش', category: 'critical' },
      { pattern: /fatal/gi, weight: 3, label: 'فتال', category: 'critical' },
      { pattern: /undefined|null pointer|NaN/gi, weight: 1.5, label: 'مقدار نامعتبر', category: 'runtime' },
      { pattern: /syntax error|parse error/gi, weight: 2, label: 'خطای سینتکس', category: 'syntax' },
      { pattern: /build failed|compilation error/gi, weight: 3, label: 'خطای بیلد', category: 'build' },
      { pattern: /tests? failed|\d+ failing/gi, weight: 2.5, label: 'تست ناموفق', category: 'test' },
      { pattern: /timeout|timed? out/gi, weight: 2, label: 'تایم‌اوت', category: 'network' },
      { pattern: /connection refused|network error/gi, weight: 2, label: 'خطای شبکه', category: 'network' },
      { pattern: /out of memory|heap/gi, weight: 2.5, label: 'کمبود حافظه', category: 'memory' },
      { pattern: /permission denied|access denied|unauthorized/gi, weight: 2, label: 'دسترسی رد شد', category: 'permission' },
      { pattern: /not found|404|missing/gi, weight: 1.5, label: 'یافت نشد', category: 'notfound' },
      { pattern: /type(?:error)?:|cannot read property/gi, weight: 2, label: 'خطای نوع', category: 'type' }
    ],
    WARNING: [
      { pattern: /warning(?:s)?:/gi, weight: 1, label: 'هشدار' },
      { pattern: /deprecated/gi, weight: 1.5, label: 'منسوخ شده' },
      { pattern: /⚠️|⚡/g, weight: 1.5, label: 'ایموجی هشدار' },
      { pattern: /TODO|FIXME|HACK/g, weight: 0.5, label: 'یادآوری' },
      { pattern: /slow|performance/gi, weight: 1, label: 'عملکرد' },
      { pattern: /insecure|vulnerable/gi, weight: 2, label: 'امنیتی' }
    ],
    PROGRESS: [
      { pattern: /(\d+)%/g, extract: true, label: 'درصد پیشرفت' },
      { pattern: /step (\d+)(?:\/| of )(\d+)/gi, extract: true, label: 'مرحله' },
      { pattern: /(\d+)\/(\d+) (?:tests?|tasks?|items?)/gi, extract: true, label: 'تکمیل شده' },
      { pattern: /ETA:?\s*(\d+\s*(?:min|sec|hour|m|s|h))/gi, extract: true, label: 'زمان باقیمانده' }
    ]
  },
  
  // راه‌حل‌های پیشنهادی بر اساس نوع خطا
  SOLUTIONS: {
    syntax: [
      'بررسی سینتکس کد در خط ذکر شده',
      'اجرای linter برای شناسایی خطاهای سینتکس',
      'بررسی براکت‌ها و پرانتزها'
    ],
    runtime: [
      'بررسی مقادیر null/undefined قبل از استفاده',
      'افزودن بلوک try-catch برای مدیریت استثناها',
      'بررسی نوع داده‌های ورودی'
    ],
    build: [
      'پاک کردن کش و rebuild',
      'بررسی وابستگی‌های پروژه',
      'آپدیت نسخه کامپایلر یا ابزار بیلد'
    ],
    test: [
      'بررسی تست‌های ناموفق به صورت جداگانه',
      'آپدیت snapshot های تست',
      'بررسی mock ها و stub ها'
    ],
    network: [
      'بررسی اتصال شبکه',
      'افزایش timeout',
      'بررسی endpoint های API'
    ],
    memory: [
      'افزایش حافظه تخصیص داده شده',
      'بهینه‌سازی استفاده از حافظه',
      'بررسی memory leak ها'
    ],
    permission: [
      'بررسی مجوزهای دسترسی',
      'لاگین مجدد یا رفرش توکن',
      'بررسی تنظیمات CORS'
    ],
    notfound: [
      'بررسی مسیر فایل یا URL',
      'اطمینان از وجود فایل یا منبع',
      'بررسی نام فایل (حساسیت به حروف بزرگ/کوچک)'
    ],
    type: [
      'بررسی نوع داده‌های ورودی/خروجی',
      'افزودن type checking',
      'بررسی تبدیل نوع‌ها'
    ],
    generic: [
      'بررسی لاگ کامل برای جزئیات بیشتر',
      'جستجوی پیام خطا در اینترنت',
      'بررسی documentation'
    ],
    critical: [
      '⚠️ خطای بحرانی - نیاز به بررسی فوری',
      'ریستارت سرویس یا اپلیکیشن',
      'بررسی منابع سیستم (CPU, RAM, Disk)'
    ]
  },
  
  // آستانه‌های تصمیم‌گیری
  THRESHOLDS: {
    AUTO_ADVANCE: { minSuccess: 3, maxError: 0, maxWarning: 3 },
    SUGGEST_ADVANCE: { minSuccess: 2, maxError: 1, maxWarning: 5 },
    NEED_REVIEW: { minError: 1, maxError: 3 },
    AUTO_ROLLBACK: { minError: 5 },
    CRITICAL_ALERT: { minCritical: 1 }
  }
};

/**
 * ✅ v16.0: تحلیل هوشمند لاگ با شناسایی الگو و پیشنهاد راه‌حل
 * @param {string} projectId - شناسه پروژه
 * @param {string} logContent - محتوای لاگ
 */
function analyzeLogAndUpdatePhase(projectId, logContent) {
  try {
    Logger.log('🔍 تحلیل هوشمند لاگ برای پروژه: ' + projectId);
    
    const analysis = {
      success: { count: 0, weighted: 0, matches: [] },
      error: { count: 0, weighted: 0, matches: [], categories: {} },
      warning: { count: 0, weighted: 0, matches: [] },
      progress: { percentage: null, step: null, total: null, eta: null }
    };
    
    // تحلیل الگوهای موفقیت
    for (const { pattern, weight, label } of INTELLIGENT_CONFIG.PATTERNS.SUCCESS) {
      const matches = logContent.match(pattern);
      if (matches) {
        analysis.success.count += matches.length;
        analysis.success.weighted += matches.length * weight;
        analysis.success.matches.push({ label, count: matches.length });
      }
    }
    
    // تحلیل الگوهای خطا با دسته‌بندی
    for (const { pattern, weight, label, category } of INTELLIGENT_CONFIG.PATTERNS.ERROR) {
      const matches = logContent.match(pattern);
      if (matches) {
        analysis.error.count += matches.length;
        analysis.error.weighted += matches.length * weight;
        analysis.error.matches.push({ label, count: matches.length, category });
        
        // دسته‌بندی خطاها
        if (!analysis.error.categories[category]) {
          analysis.error.categories[category] = 0;
        }
        analysis.error.categories[category] += matches.length;
      }
    }
    
    // تحلیل هشدارها
    for (const { pattern, weight, label } of INTELLIGENT_CONFIG.PATTERNS.WARNING) {
      const matches = logContent.match(pattern);
      if (matches) {
        analysis.warning.count += matches.length;
        analysis.warning.weighted += matches.length * weight;
        analysis.warning.matches.push({ label, count: matches.length });
      }
    }
    
    // استخراج پیشرفت
    const percentMatch = logContent.match(/(\d+)%/);
    if (percentMatch) {
      analysis.progress.percentage = parseInt(percentMatch[1]);
    }
    
    const stepMatch = logContent.match(/step (\d+)(?:\/| of )(\d+)/i);
    if (stepMatch) {
      analysis.progress.step = parseInt(stepMatch[1]);
      analysis.progress.total = parseInt(stepMatch[2]);
    }
    
    // تعیین وضعیت و تصمیم
    const decision = makeIntelligentDecision(analysis);
    
    // تولید پیشنهادات راه‌حل
    const solutions = generateSolutions(analysis);
    
    // ذخیره تحلیل در پروژه
    saveAnalysisToProject(projectId, analysis, decision);
    
    // ثبت در ژورنال
    logToJournal('intelligent_log_analysis', 'project', {
      status: decision.status,
      analysis: {
        successCount: analysis.success.count,
        errorCount: analysis.error.count,
        warningCount: analysis.warning.count,
        errorCategories: analysis.error.categories
      },
      decision: decision.action,
      confidence: decision.confidence
    }, projectId);
    
    return {
      success: true,
      status: decision.status,
      analysis: {
        successCount: analysis.success.count,
        successWeighted: analysis.success.weighted,
        errorCount: analysis.error.count,
        errorWeighted: analysis.error.weighted,
        warningCount: analysis.warning.count,
        errorCategories: analysis.error.categories,
        progress: analysis.progress
      },
      decision: decision,
      solutions: solutions,
      recommendation: decision.recommendation,
      shouldAdvance: decision.shouldAdvance,
      shouldRollback: decision.shouldRollback
    };
    
  } catch (error) {
    Logger.log('❌ خطا در تحلیل هوشمند لاگ: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * ✅ v16.0: تصمیم‌گیری هوشمند بر اساس تحلیل
 */
function makeIntelligentDecision(analysis) {
  const thresholds = INTELLIGENT_CONFIG.THRESHOLDS;
  
  let status = 'unknown';
  let action = 'review';
  let recommendation = '';
  let shouldAdvance = false;
  let shouldRollback = false;
  let confidence = 0;
  
  const { success, error, warning } = analysis;
  
  // بررسی خطاهای بحرانی
  const criticalCount = (error.categories.critical || 0) + (error.categories.memory || 0);
  if (criticalCount >= thresholds.CRITICAL_ALERT.minCritical) {
    status = 'critical';
    action = 'stop';
    recommendation = '🚨 خطای بحرانی! نیاز به بررسی فوری. عملیات متوقف شود.';
    shouldRollback = true;
    confidence = 0.95;
    return { status, action, recommendation, shouldAdvance, shouldRollback, confidence };
  }
  
  // پیشرفت خودکار
  if (success.count >= thresholds.AUTO_ADVANCE.minSuccess && 
      error.count <= thresholds.AUTO_ADVANCE.maxError &&
      warning.count <= thresholds.AUTO_ADVANCE.maxWarning) {
    status = 'success';
    action = 'auto_advance';
    recommendation = '✅ همه چیز موفق! آماده پیشرفت خودکار به مرحله بعد.';
    shouldAdvance = true;
    confidence = 0.9;
  }
  // پیشنهاد پیشرفت
  else if (success.count >= thresholds.SUGGEST_ADVANCE.minSuccess && 
           error.count <= thresholds.SUGGEST_ADVANCE.maxError &&
           warning.count <= thresholds.SUGGEST_ADVANCE.maxWarning) {
    status = 'partial_success';
    action = 'suggest_advance';
    recommendation = '✓ عمدتاً موفق با برخی هشدارها. آیا می‌خواهید ادامه دهید؟';
    shouldAdvance = true;
    confidence = 0.7;
  }
  // نیاز به بررسی
  else if (error.count >= thresholds.NEED_REVIEW.minError && 
           error.count <= thresholds.NEED_REVIEW.maxError) {
    status = 'needs_review';
    action = 'review';
    recommendation = '⚠️ برخی خطاها شناسایی شد. لطفاً بررسی کنید.';
    confidence = 0.6;
  }
  // برگشت خودکار
  else if (error.count >= thresholds.AUTO_ROLLBACK.minError) {
    status = 'failure';
    action = 'auto_rollback';
    recommendation = '❌ خطاهای متعدد! پیشنهاد برگشت به مرحله قبل.';
    shouldRollback = true;
    confidence = 0.85;
  }
  // وضعیت نامشخص
  else {
    status = 'unknown';
    action = 'manual_check';
    recommendation = '🔍 وضعیت نامشخص. لطفاً دستی بررسی کنید.';
    confidence = 0.3;
  }
  
  return { status, action, recommendation, shouldAdvance, shouldRollback, confidence };
}

/**
 * ✅ v16.0: تولید راه‌حل‌های پیشنهادی بر اساس نوع خطا
 */
function generateSolutions(analysis) {
  const solutions = [];
  const categories = analysis.error.categories;
  
  // اضافه کردن راه‌حل‌ها بر اساس دسته‌بندی خطاها
  for (const [category, count] of Object.entries(categories)) {
    if (count > 0 && INTELLIGENT_CONFIG.SOLUTIONS[category]) {
      solutions.push({
        category: category,
        count: count,
        suggestions: INTELLIGENT_CONFIG.SOLUTIONS[category]
      });
    }
  }
  
  // اگر هیچ راه‌حل خاصی نبود، راه‌حل‌های عمومی
  if (solutions.length === 0 && analysis.error.count > 0) {
    solutions.push({
      category: 'generic',
      count: analysis.error.count,
      suggestions: INTELLIGENT_CONFIG.SOLUTIONS.generic
    });
  }
  
  return solutions;
}

/**
 * ✅ v16.0: ذخیره تحلیل در پروژه برای یادگیری
 */
function saveAnalysisToProject(projectId, analysis, decision) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context) return;
    
    // ذخیره در تاریخچه تحلیل‌ها
    if (!context.analysisHistory) {
      context.analysisHistory = [];
    }
    
    context.analysisHistory.push({
      timestamp: new Date().toISOString(),
      analysis: {
        success: analysis.success.count,
        error: analysis.error.count,
        warning: analysis.warning.count,
        categories: analysis.error.categories
      },
      decision: decision.action,
      status: decision.status
    });
    
    // نگه‌داری فقط ۵۰ تحلیل آخر
    if (context.analysisHistory.length > 50) {
      context.analysisHistory = context.analysisHistory.slice(-50);
    }
    
    // به‌روزرسانی آمار کلی
    if (!context.stats) {
      context.stats = { totalAnalyses: 0, autoAdvances: 0, rollbacks: 0 };
    }
    context.stats.totalAnalyses++;
    if (decision.shouldAdvance) context.stats.autoAdvances++;
    if (decision.shouldRollback) context.stats.rollbacks++;
    
    saveSmartProjectContext(projectId, context);
  } catch (e) {
    Logger.log('⚠️ خطا در ذخیره تحلیل: ' + e);
  }
}

/**
 * پیشرفت خودکار بر اساس تحلیل
 */
function autoAdvancePhase(projectId, logContent) {
  const analysis = analyzeLogAndUpdatePhase(projectId, logContent);
  
  if (analysis.success && analysis.shouldAdvance) {
    // تأیید نهایی با یک تست دیگر
    const confirmResult = apiNextPhase(projectId);
    
    logToJournal('auto_phase_advance', 'project', {
      analysis: analysis.analysis,
      newPhase: confirmResult.currentPhase
    }, projectId);
    
    return {
      success: true,
      action: 'advanced',
      analysis: analysis,
      phaseResult: confirmResult
    };
  }
  
  if (analysis.success && analysis.shouldRollback) {
    logToJournal('auto_rollback_suggested', 'project', {
      analysis: analysis.analysis
    }, projectId);
    
    return {
      success: true,
      action: 'rollback_suggested',
      analysis: analysis,
      message: 'پیشنهاد برگشت به مرحله قبل به دلیل خطاهای متعدد'
    };
  }
  
  return {
    success: true,
    action: 'none',
    analysis: analysis
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 END OF EXTENDED SYSTEMS
// ═══════════════════════════════════════════════════════════════════════════════
// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SMART PROJECT SYSTEM v2.0 - سیستم پروژه هوشمند کامل
// ═══════════════════════════════════════════════════════════════════════════════
// این سیستم یک مدیریت پروژه کاملاً هوشمند و خودکار ارائه می‌دهد
// ═══════════════════════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 ARCHIVED MODELS MANAGEMENT - مدیریت مدل‌های آرشیو شده
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ذخیره آرشیو مدل‌ها
 */
function getArchivedModelsDB() {
  const props = PropertiesService.getScriptProperties();
  const data = props.getProperty('ARCHIVED_MODELS_DB');
  return data ? JSON.parse(data) : { models: {}, history: [] };
}

function saveArchivedModelsDB(db) {
  const props = PropertiesService.getScriptProperties();
  props.setProperty('ARCHIVED_MODELS_DB', JSON.stringify(db));
}

/**
 * آرشیو کردن مدل با دلیل و ثبت تاریخچه
 */
function archiveModelWithReason(modelId, reason, errorDetails = null) {
  try {
    const db = getArchivedModelsDB();
    
    db.models[modelId] = {
      archivedAt: new Date().toISOString(),
      reason: reason,
      errorDetails: errorDetails,
      errorCount: (db.models[modelId]?.errorCount || 0) + 1,
      canReactivate: true
    };
    
    db.history.push({
      action: 'archive',
      modelId: modelId,
      reason: reason,
      timestamp: new Date().toISOString()
    });
    
    // محدود کردن تاریخچه به 500 رکورد
    if (db.history.length > 500) {
      db.history = db.history.slice(-500);
    }
    
    saveArchivedModelsDB(db);
    
    // غیرفعال کردن در MODEL_REGISTRY
    if (typeof MODEL_REGISTRY !== 'undefined' && MODEL_REGISTRY[modelId]) {
      MODEL_REGISTRY[modelId].enabled = false;
      MODEL_REGISTRY[modelId].archived = true;
      MODEL_REGISTRY[modelId].archiveReason = reason;
    }
    
    // ثبت در ژورنال
    logToJournal('model_archived', 'model', { modelId, reason, errorDetails });
    
    Logger.log('📦 مدل آرشیو شد: ' + modelId + ' - دلیل: ' + reason);
    
    return { success: true, modelId: modelId };
  } catch (error) {
    Logger.log('❌ خطا در آرشیو مدل: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * فعال‌سازی مجدد مدل
 */
function reactivateModel(modelId) {
  try {
    const db = getArchivedModelsDB();
    
    if (db.models[modelId]) {
      db.models[modelId].reactivatedAt = new Date().toISOString();
      db.models[modelId].canReactivate = true;
      delete db.models[modelId].archivedAt;
      
      db.history.push({
        action: 'reactivate',
        modelId: modelId,
        timestamp: new Date().toISOString()
      });
      
      saveArchivedModelsDB(db);
    }
    
    // فعال کردن در MODEL_REGISTRY
    if (typeof MODEL_REGISTRY !== 'undefined' && MODEL_REGISTRY[modelId]) {
      MODEL_REGISTRY[modelId].enabled = true;
      MODEL_REGISTRY[modelId].archived = false;
    }
    
    logToJournal('model_reactivated', 'model', { modelId });
    
    return { success: true, modelId: modelId };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * ثبت خطای مدل و آرشیو خودکار
 */
function recordModelFailure(modelId, errorMessage, projectId = null) {
  const db = getArchivedModelsDB();
  const ERROR_THRESHOLD = 3; // تعداد خطا برای آرشیو خودکار
  
  if (!db.models[modelId]) {
    db.models[modelId] = { errorCount: 0, errors: [] };
  }
  
  db.models[modelId].errorCount = (db.models[modelId].errorCount || 0) + 1;
  db.models[modelId].lastError = {
    message: errorMessage,
    projectId: projectId,
    timestamp: new Date().toISOString()
  };
  
  db.models[modelId].errors = db.models[modelId].errors || [];
  db.models[modelId].errors.push({
    message: errorMessage,
    timestamp: new Date().toISOString()
  });
  
  // فقط 20 خطای آخر
  if (db.models[modelId].errors.length > 20) {
    db.models[modelId].errors = db.models[modelId].errors.slice(-20);
  }
  
  saveArchivedModelsDB(db);
  
  // آرشیو خودکار
  if (db.models[modelId].errorCount >= ERROR_THRESHOLD && !db.models[modelId].archivedAt) {
    Logger.log('⚠️ آرشیو خودکار مدل ' + modelId + ' به دلیل ' + ERROR_THRESHOLD + ' خطا');
    archiveModelWithReason(modelId, 'آرشیو خودکار - ' + ERROR_THRESHOLD + ' خطای متوالی', errorMessage);
    return { archived: true, errorCount: db.models[modelId].errorCount };
  }
  
  return { archived: false, errorCount: db.models[modelId].errorCount };
}

/**
 * دریافت لیست مدل‌های فعال (غیر آرشیو)
 */
function getActiveModelsOnly() {
  const db = getArchivedModelsDB();
  const activeModels = {};
  
  if (typeof MODEL_REGISTRY === 'undefined') return {};
  
  for (const [modelId, model] of Object.entries(MODEL_REGISTRY)) {
    const isArchived = db.models[modelId]?.archivedAt;
    if (!isArchived && model.enabled !== false) {
      activeModels[modelId] = {
        ...model,
        id: modelId,
        errorCount: db.models[modelId]?.errorCount || 0
      };
    }
  }
  
  return activeModels;
}

/**
 * گزارش کامل مدل‌ها
 */
function getModelsFullReport() {
  const db = getArchivedModelsDB();
  
  const report = {
    total: 0,
    active: 0,
    archived: 0,
    withErrors: 0,
    activeModels: [],
    archivedModels: [],
    recentErrors: []
  };
  
  if (typeof MODEL_REGISTRY === 'undefined') return report;
  
  for (const [modelId, model] of Object.entries(MODEL_REGISTRY)) {
    report.total++;
    
    const archiveInfo = db.models[modelId];
    const isArchived = archiveInfo?.archivedAt;
    
    const modelData = {
      id: modelId,
      name: model.name,
      provider: model.provider,
      errorCount: archiveInfo?.errorCount || 0,
      lastError: archiveInfo?.lastError
    };
    
    if (isArchived) {
      report.archived++;
      modelData.archivedAt = archiveInfo.archivedAt;
      modelData.archiveReason = archiveInfo.reason;
      report.archivedModels.push(modelData);
    } else if (model.enabled !== false) {
      report.active++;
      report.activeModels.push(modelData);
    }
    
    if (archiveInfo?.errorCount > 0) {
      report.withErrors++;
    }
  }
  
  // خطاهای اخیر
  report.recentErrors = db.history
    .filter(h => h.action === 'archive')
    .slice(-10)
    .reverse();
  
  return report;
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SMART MODEL SELECTION - انتخاب هوشمند مدل
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * انتخاب بهترین مدل برای پروژه بر اساس نوع و محتوا
 */
function selectOptimalModel(projectType, taskDescription, complexity = 'intermediate') {
  const activeModels = getActiveModelsOnly();
  const db = getArchivedModelsDB();
  
  // امتیازدهی مدل‌ها
  const scoredModels = [];
  
  // تعیین قابلیت‌های مورد نیاز بر اساس نوع پروژه
  const requiredCapabilities = getRequiredCapabilities(projectType);
  
  for (const [modelId, model] of Object.entries(activeModels)) {
    let score = 50; // امتیاز پایه
    
    // بررسی قابلیت‌ها
    const capabilities = model.capabilities || [];
    for (const cap of requiredCapabilities) {
      if (capabilities.includes(cap)) {
        score += 15;
      }
    }
    
    // بررسی نقاط قوت
    const strengths = model.strengths || [];
    for (const strength of strengths) {
      if (requiredCapabilities.includes(strength)) {
        score += 10;
      }
    }
    
    // کاهش امتیاز برای مدل‌های با خطا
    const errorCount = db.models[modelId]?.errorCount || 0;
    score -= errorCount * 5;
    
    // افزایش امتیاز برای مدل‌های با اولویت بالا
    score += (10 - (model.priority || 5)) * 3;
    
    // تنظیم بر اساس پیچیدگی
    if (complexity === 'expert' && model.contextWindow > 100000) {
      score += 20;
    } else if (complexity === 'beginner' && model.costPer1kTokens < 0.01) {
      score += 15;
    }
    
    scoredModels.push({
      id: modelId,
      name: model.name,
      provider: model.provider,
      score: Math.max(0, Math.min(100, score)),
      capabilities: capabilities,
      errorCount: errorCount
    });
  }
  
  // مرتب‌سازی بر اساس امتیاز
  scoredModels.sort((a, b) => b.score - a.score);
  
  // انتخاب 3 مدل برتر
  const topModels = scoredModels.slice(0, 3);
  
  Logger.log('🎯 مدل‌های انتخابی: ' + topModels.map(m => m.name).join(', '));
  
  return {
    success: true,
    primaryModel: topModels[0],
    alternativeModels: topModels.slice(1),
    allScored: scoredModels.slice(0, 10)
  };
}

/**
 * تعیین قابلیت‌های مورد نیاز
 */
function getRequiredCapabilities(projectType) {
  const capMap = {
    'coding': ['code', 'reasoning', 'text'],
    'learning': ['text', 'reasoning', 'long-context'],
    'research': ['text', 'reasoning', 'long-context'],
    'writing': ['text', 'creative', 'long-context'],
    'design': ['text', 'creative', 'image-analysis'],
    'analysis': ['text', 'reasoning', 'data-analysis'],
    'trading': ['code', 'reasoning', 'data-analysis'],
    'custom': ['text', 'reasoning']
  };
  
  return capMap[projectType] || capMap['custom'];
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 AUTOMATIC PHASE DETECTION - تشخیص خودکار فاز
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * تحلیل پاسخ و تعیین وضعیت فاز
 */
function analyzeResponseForPhaseStatus(response, projectContext) {
  try {
    // الگوهای نشان‌دهنده تکمیل
    const completionPatterns = [
      /کار تکمیل شد/i,
      /با موفقیت انجام شد/i,
      /این مرحله به پایان رسید/i,
      /آماده مرحله بعد/i,
      /successfully completed/i,
      /task completed/i,
      /phase complete/i,
      /ready for next/i,
      /✅|✓|👍/
    ];
    
    // الگوهای نشان‌دهنده نیاز به تکرار
    const retryPatterns = [
      /نیاز به اصلاح/i,
      /خطا وجود دارد/i,
      /باید دوباره/i,
      /مشکل/i,
      /error|failed|fix|bug/i,
      /❌|✗|👎/
    ];
    
    // الگوهای نشان‌دهنده نیاز به ورودی بیشتر
    const needInputPatterns = [
      /لطفاً مشخص کنید/i,
      /به اطلاعات بیشتری نیاز/i,
      /کدام گزینه/i,
      /please provide/i,
      /need more information/i,
      /which option/i,
      /\?$/
    ];
    
    let status = 'in_progress';
    let confidence = 0.5;
    let suggestion = '';
    
    // بررسی الگوها
    for (const pattern of completionPatterns) {
      if (pattern.test(response)) {
        status = 'completed';
        confidence += 0.15;
        suggestion = 'این مرحله به نظر تکمیل شده. آیا به مرحله بعد برویم؟';
      }
    }
    
    for (const pattern of retryPatterns) {
      if (pattern.test(response)) {
        status = 'needs_retry';
        confidence += 0.1;
        suggestion = 'به نظر مشکلی وجود دارد. بررسی و اصلاح توصیه می‌شود.';
      }
    }
    
    for (const pattern of needInputPatterns) {
      if (pattern.test(response)) {
        status = 'waiting_input';
        confidence += 0.1;
        suggestion = 'AI منتظر پاسخ یا ورودی شماست.';
      }
    }
    
    // تحلیل کدها
    const hasCode = /```[\s\S]*```/.test(response);
    if (hasCode) {
      confidence += 0.1;
      if (status === 'completed') {
        suggestion += ' کد جدید تولید شده است.';
      }
    }
    
    return {
      status: status,
      confidence: Math.min(1, confidence),
      suggestion: suggestion,
      hasCode: hasCode,
      autoAdvance: status === 'completed' && confidence > 0.7
    };
    
  } catch (error) {
    Logger.log('خطا در تحلیل پاسخ: ' + error);
    return { status: 'unknown', confidence: 0, suggestion: '' };
  }
}

/**
 * تحلیل لاگ ترمینال یا کنسول
 */
function analyzeTerminalLog(logContent, expectedOutcome = null) {
  try {
    const analysis = {
      status: 'unknown',
      errors: [],
      warnings: [],
      successes: [],
      metrics: {}
    };
    
    const lines = logContent.split('\n');
    
    for (const line of lines) {
      const lowerLine = line.toLowerCase();
      
      // خطاها
      if (/error|exception|failed|fatal|crash/i.test(line)) {
        analysis.errors.push(line.trim());
      }
      
      // هشدارها
      if (/warning|warn|deprecated/i.test(line)) {
        analysis.warnings.push(line.trim());
      }
      
      // موفقیت‌ها
      if (/success|passed|completed|done|ok/i.test(line)) {
        analysis.successes.push(line.trim());
      }
      
      // متریک‌ها
      const testMatch = line.match(/(\d+)\s*(tests?|specs?)\s*(passed|failed)/i);
      if (testMatch) {
        analysis.metrics.tests = analysis.metrics.tests || { passed: 0, failed: 0 };
        if (/passed/i.test(testMatch[3])) {
          analysis.metrics.tests.passed += parseInt(testMatch[1]);
        } else {
          analysis.metrics.tests.failed += parseInt(testMatch[1]);
        }
      }
    }
    
    // تعیین وضعیت کلی
    if (analysis.errors.length === 0 && analysis.successes.length > 0) {
      analysis.status = 'success';
      analysis.recommendation = 'همه چیز موفق بود. می‌توانید به مرحله بعد بروید.';
      analysis.canAdvance = true;
    } else if (analysis.errors.length > 0 && analysis.errors.length <= 2) {
      analysis.status = 'partial_success';
      analysis.recommendation = 'چند خطای جزئی وجود دارد که باید رفع شوند.';
      analysis.canAdvance = false;
    } else if (analysis.errors.length > 2) {
      analysis.status = 'failure';
      analysis.recommendation = 'خطاهای متعدد. نیاز به بررسی و احتمالاً برگشت به مرحله قبل.';
      analysis.canAdvance = false;
      analysis.shouldRollback = analysis.errors.length > 5;
    } else {
      analysis.status = 'neutral';
      analysis.recommendation = 'وضعیت نامشخص. لاگ را بررسی کنید.';
      analysis.canAdvance = false;
    }
    
    return analysis;
    
  } catch (error) {
    return { status: 'error', error: error.message };
  }
}

/**
 * پیشرفت خودکار فاز بر اساس تحلیل
 */
function autoProgressPhase(projectId, analysisResult) {
  try {
    const projectData = loadPersistentProject(projectId);
    if (!projectData.success) return projectData;
    
    const context = projectData.context;
    const currentPhaseIndex = context.phases.findIndex(p => p.status === 'active');
    
    if (currentPhaseIndex === -1) {
      return { success: false, error: 'فاز فعالی یافت نشد' };
    }
    
    let action = 'none';
    let message = '';
    
    if (analysisResult.canAdvance || analysisResult.autoAdvance) {
      // پیشرفت به فاز بعدی
      const result = startPersistentNextPhase(projectId);
      if (result.success) {
        action = 'advanced';
        message = 'به صورت خودکار به فاز بعدی رفتیم: ' + result.newPhase;
        
        logToJournal('auto_phase_advance', 'project', {
          fromPhase: currentPhaseIndex,
          toPhase: currentPhaseIndex + 1,
          reason: 'تحلیل خودکار'
        }, projectId);
      }
    } else if (analysisResult.shouldRollback) {
      // برگشت به فاز قبلی
      const result = rollbackPersistentPhase(projectId, 'برگشت خودکار به دلیل خطاهای متعدد');
      if (result.success) {
        action = 'rollback';
        message = 'به دلیل خطاها به فاز قبلی برگشتیم';
        
        logToJournal('auto_phase_rollback', 'project', {
          fromPhase: currentPhaseIndex,
          reason: analysisResult.recommendation
        }, projectId);
      }
    }
    
    return {
      success: true,
      action: action,
      message: message,
      analysis: analysisResult
    };
    
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 ENHANCED PROJECT MESSAGE - ارسال پیام پیشرفته
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ارسال پیام به پروژه با تحلیل خودکار
 */
function sendSmartProjectMessage(projectId, message, attachments = [], options = {}) {
  try {
    Logger.log('📨 ارسال پیام هوشمند به پروژه: ' + projectId);
    
    // بارگذاری پروژه
    const projectData = loadPersistentProject(projectId);
    if (!projectData.success) {
      return { success: false, error: projectData.error };
    }
    
    const context = projectData.context;
    
    // انتخاب هوشمند مدل
    let selectedModel;
    if (options.model) {
      selectedModel = { id: options.model };
    } else {
      const modelSelection = selectOptimalModel(
        context.project.type, 
        message, 
        context.project.complexity
      );
      selectedModel = modelSelection.primaryModel;
      
      if (!selectedModel) {
        return { success: false, error: 'هیچ مدل فعالی یافت نشد' };
      }
    }
    
    // پردازش فایل‌های پیوست
    const processedAttachments = [];
    for (const att of attachments) {
      if (att.type === 'file' && att.content) {
        // ذخیره فایل در پروژه
        const saveResult = apiUploadToProject(
          projectId, 
          att.name, 
          att.content, 
          att.mimeType || 'application/octet-stream'
        );
        if (saveResult.success) {
          processedAttachments.push({
            name: att.name,
            fileId: saveResult.fileId,
            url: saveResult.url
          });
        }
      }
    }
    
    // ساخت پرامپت سیستم
    const systemPrompt = buildPersistentProjectSystemPrompt(context, true);
    
    // افزودن اطلاعات فایل‌های پیوست
    let fullMessage = message;
    if (processedAttachments.length > 0) {
      fullMessage += '\n\nفایل‌های پیوست:\n' + 
        processedAttachments.map(a => '- ' + a.name).join('\n');
    }
    
    const finalPrompt = `${systemPrompt}\n\n---\n\nپیام کاربر:\n${fullMessage}`;
    
    // ارسال به مدل
    const startTime = Date.now();
    let response;
    let modelUsed = selectedModel.id;
    
    try {
      response = callModel(selectedModel.id, finalPrompt, attachments);
    } catch (modelError) {
      // ثبت خطا و تلاش با مدل جایگزین
      Logger.log('⚠️ خطا در مدل ' + selectedModel.id + ': ' + modelError.message);
      recordModelFailure(selectedModel.id, modelError.message, projectId);
      
      // تلاش با مدل جایگزین
      const alternativeModels = ['gpt-4-turbo', 'claude-sonnet-4-20250514', 'gemini-2.5-pro'];
      for (const altModel of alternativeModels) {
        if (altModel !== selectedModel.id) {
          try {
            response = callModel(altModel, finalPrompt, attachments);
            modelUsed = altModel;
            Logger.log('✅ مدل جایگزین استفاده شد: ' + altModel);
            break;
          } catch (altError) {
            recordModelFailure(altModel, altError.message, projectId);
          }
        }
      }
      
      if (!response) {
        return { success: false, error: 'همه مدل‌ها با خطا مواجه شدند' };
      }
    }
    
    const duration = (Date.now() - startTime) / 1000;
    
    // ✅ v17.1.4: به‌روزرسانی مدل فعال در context
    context.activeModel = modelUsed;
    
    // اضافه کردن به تایم‌لاین
    if (!context.timeline) {
      context.timeline = [];
    }
    context.timeline.push({
      type: 'AI_INTERACTION',
      message: `مکالمه با ${getModelDisplayName(modelUsed)}`,
      timestamp: new Date().toISOString()
    });
    
    // ذخیره مکالمه
    const conversationId = 'conv_' + Date.now();
    if (!context.conversations) {
      context.conversations = [];
    }
    context.conversations.push({
      id: conversationId,
      userMessage: fullMessage,
      aiResponse: response,
      model: modelUsed,
      modelName: getModelDisplayName(modelUsed),
      duration: duration,
      timestamp: new Date().toISOString()
    });
    
    // ذخیره context به‌روز شده
    saveSmartProjectContext(projectId, context);
    
    const modelResponses = [{
      model: modelUsed,
      response: response,
      duration: duration,
      score: 75
    }];
    
    addPersistentProjectConversation(projectId, fullMessage, modelResponses);
    
    // استخراج کدها
    const codeBlocks = extractPersistentCodeFromResponse(response);
    for (const block of codeBlocks) {
      savePersistentProjectFile(
        projectId,
        `code_${Date.now()}.${getPersistentExtensionForLanguage(block.language)}`,
        block.code,
        block.language,
        'code',
        'کد استخراج شده از پاسخ'
      );
    }
    
    // تحلیل خودکار پاسخ
    const phaseAnalysis = analyzeResponseForPhaseStatus(response, context);
    
    // ثبت در ژورنال
    logToJournal('message_sent', 'project', {
      projectId: projectId,
      model: modelUsed,
      duration: duration,
      hasAttachments: processedAttachments.length > 0,
      phaseStatus: phaseAnalysis.status
    }, projectId);
    
    return {
      success: true,
      conversationId: conversationId,
      model: modelUsed,
      response: response,
      duration: duration,
      codeBlocks: codeBlocks,
      attachments: processedAttachments,
      phaseAnalysis: phaseAnalysis,
      currentPhase: context.currentPhase
    };
    
  } catch (error) {
    Logger.log('❌ خطا در ارسال پیام: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * ارسال لاگ و تحلیل خودکار
 */
function submitLogForAnalysis(projectId, logContent, autoProgress = true) {
  try {
    // ذخیره لاگ
    savePersistentProjectLog(projectId, logContent, 'terminal_log');
    
    // تحلیل لاگ
    const analysis = analyzeTerminalLog(logContent);
    
    // ثبت در ژورنال
    logToJournal('log_submitted', 'project', {
      status: analysis.status,
      errorCount: analysis.errors.length,
      warningCount: analysis.warnings.length
    }, projectId);
    
    // پیشرفت خودکار
    let progressResult = null;
    if (autoProgress) {
      progressResult = autoProgressPhase(projectId, analysis);
    }
    
    return {
      success: true,
      analysis: analysis,
      progressResult: progressResult
    };
    
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 FILE UPLOAD HANDLER - مدیریت آپلود فایل
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * آپلود فایل به پروژه
 */
function uploadFileToProject(projectId, fileName, fileContentBase64, mimeType) {
  try {
    Logger.log('📤 آپلود فایل: ' + fileName + ' به پروژه: ' + projectId);
    
    // تبدیل از Base64
    const fileContent = Utilities.base64Decode(fileContentBase64);
    const blob = Utilities.newBlob(fileContent, mimeType, fileName);
    
    // دریافت اطلاعات پروژه
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    
    if (!projectInfo) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    // دریافت فولدر Uploads
    const projectFolder = DriveApp.getFolderById(projectInfo.folderId);
    const uploadsFolder = getOrCreatePersistentFolder(projectFolder, '01_Uploads');
    
    // ایجاد فایل
    const file = uploadsFolder.createFile(blob);
    
    // به‌روزرسانی context
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    const context = JSON.parse(contextFile.getBlob().getDataAsString());
    
    context.files.uploaded.push({
      id: file.getId(),
      name: fileName,
      url: file.getUrl(),
      mimeType: mimeType,
      size: file.getSize(),
      uploadedAt: new Date().toISOString()
    });
    
    contextFile.setContent(JSON.stringify(context, null, 2));
    
    // ثبت در ژورنال
    logToJournal('file_uploaded', 'file', {
      fileName: fileName,
      mimeType: mimeType,
      size: file.getSize()
    }, projectId);
    
    return {
      success: true,
      fileId: file.getId(),
      url: file.getUrl(),
      name: fileName
    };
    
  } catch (error) {
    Logger.log('❌ خطا در آپلود فایل: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * پردازش فایل ZIP
 */
function processZipFileInProject(projectId, fileId) {
  try {
    const file = DriveApp.getFileById(fileId);
    const blob = file.getBlob();
    const zipContent = Utilities.unzip(blob);
    
    const results = {
      success: true,
      totalFiles: zipContent.length,
      processed: [],
      errors: []
    };
    
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    const projectFolder = DriveApp.getFolderById(projectInfo.folderId);
    const uploadsFolder = getOrCreatePersistentFolder(projectFolder, '01_Uploads');
    
    for (const item of zipContent) {
      try {
        const fileName = item.getName();
        const createdFile = uploadsFolder.createFile(item);
        
        results.processed.push({
          name: fileName,
          fileId: createdFile.getId(),
          url: createdFile.getUrl()
        });
      } catch (itemError) {
        results.errors.push({
          name: item.getName(),
          error: itemError.message
        });
      }
    }
    
    logToJournal('zip_processed', 'file', {
      totalFiles: results.totalFiles,
      processedCount: results.processed.length,
      errorCount: results.errors.length
    }, projectId);
    
    return results;
    
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 JOURNAL SYSTEM - سیستم ژورنال کامل
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ذخیره و بازیابی ژورنال
 */
function getSystemJournal() {
  const props = PropertiesService.getScriptProperties();
  const data = props.getProperty('SYSTEM_JOURNAL_V2');
  return data ? JSON.parse(data) : [];
}

function saveSystemJournal(journal) {
  const props = PropertiesService.getScriptProperties();
  // محدود کردن به 2000 رکورد
  if (journal.length > 2000) {
    journal = journal.slice(-2000);
  }
  props.setProperty('SYSTEM_JOURNAL_V2', JSON.stringify(journal));
}

/**
 * ثبت رویداد در ژورنال
 */
function logToJournal(action, category, details, projectId = null) {
  try {
    const journal = getSystemJournal();
    
    const entry = {
      id: 'j_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5),
      timestamp: new Date().toISOString(),
      action: action,
      category: category,
      projectId: projectId,
      details: details
    };
    
    journal.push(entry);
    saveSystemJournal(journal);
    
    return entry;
  } catch (error) {
    Logger.log('خطا در ثبت ژورنال: ' + error);
    return null;
  }
}

/**
 * دریافت ژورنال با فیلتر
 */
function getJournalEntries(options = {}) {
  let journal = getSystemJournal();
  
  // فیلتر پروژه
  if (options.projectId) {
    journal = journal.filter(e => e.projectId === options.projectId);
  }
  
  // فیلتر دسته‌بندی
  if (options.category) {
    journal = journal.filter(e => e.category === options.category);
  }
  
  // فیلتر تاریخ
  if (options.fromDate) {
    journal = journal.filter(e => new Date(e.timestamp) >= new Date(options.fromDate));
  }
  
  if (options.toDate) {
    journal = journal.filter(e => new Date(e.timestamp) <= new Date(options.toDate));
  }
  
  // مرتب‌سازی (جدید به قدیم)
  journal.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  
  // صفحه‌بندی
  const page = options.page || 1;
  const perPage = options.perPage || 50;
  const start = (page - 1) * perPage;
  
  return {
    entries: journal.slice(start, start + perPage),
    total: journal.length,
    page: page,
    totalPages: Math.ceil(journal.length / perPage)
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SMART PROJECT CREATION - ایجاد هوشمند پروژه
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ایجاد پروژه بر اساس تحلیل هوشمند
 */
function createSmartProjectFromPrompt(userPrompt, attachments = []) {
  try {
    Logger.log('🧠 ایجاد هوشمند پروژه...');
    
    // ساخت پرامپت تحلیل
    const analysisPrompt = `تحلیل کن و اطلاعات پروژه را استخراج کن:

درخواست کاربر:
${userPrompt}

${attachments.length > 0 ? 'فایل‌های پیوست: ' + attachments.map(a => a.name).join(', ') : ''}

پاسخ فقط JSON:
{
  "projectName": "نام پروژه",
  "projectType": "coding|learning|research|writing|design|analysis|trading|custom",
  "description": "توضیح کوتاه",
  "goal": "هدف اصلی",
  "complexity": "beginner|intermediate|advanced|expert",
  "phases": [
    {"name": "نام فاز", "description": "توضیح", "steps": ["گام 1", "گام 2"]}
  ],
  "suggestedModels": ["model1", "model2"],
  "keywords": ["کلمه کلیدی"]
}`;

    // فراخوانی مدل برای تحلیل
    let projectInfo;
    try {
      const analysisResponse = callModel('gpt-4-turbo', analysisPrompt, []);
      const jsonMatch = analysisResponse.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        projectInfo = JSON.parse(jsonMatch[0]);
      }
    } catch (parseError) {
      Logger.log('⚠️ خطا در parse، استفاده از مقادیر پیش‌فرض');
    }
    
    // مقادیر پیش‌فرض
    if (!projectInfo) {
      projectInfo = {
        projectName: 'پروژه ' + new Date().toLocaleDateString('fa-IR'),
        projectType: 'custom',
        description: userPrompt.substring(0, 500),
        goal: userPrompt.substring(0, 200),
        complexity: 'intermediate',
        phases: [],
        suggestedModels: []
      };
    }
    
    // انتخاب مدل‌های مناسب
    const modelSelection = selectOptimalModel(projectInfo.projectType, userPrompt, projectInfo.complexity);
    const selectedModels = [
      modelSelection.primaryModel?.id,
      ...(modelSelection.alternativeModels || []).map(m => m.id)
    ].filter(Boolean);
    
    // ایجاد پروژه
    const createResult = createPersistentProject({
      name: projectInfo.projectName,
      type: projectInfo.projectType,
      description: projectInfo.description,
      goal: projectInfo.goal,
      complexity: projectInfo.complexity,
      models: selectedModels.length > 0 ? selectedModels : ['gpt-4-turbo', 'claude-sonnet-4-20250514'],
      customPhases: projectInfo.phases
    });
    
    if (!createResult.success) {
      return createResult;
    }
    
    // ثبت در ژورنال
    logToJournal('smart_project_created', 'project', {
      name: projectInfo.projectName,
      type: projectInfo.projectType,
      models: selectedModels
    }, createResult.projectId);
    
    return {
      success: true,
      projectId: createResult.projectId,
      projectInfo: projectInfo,
      selectedModels: selectedModels,
      folderUrl: createResult.folderUrl,
      sheetUrl: createResult.sheetUrl
    };
    
  } catch (error) {
    Logger.log('❌ خطا در ایجاد هوشمند: ' + error);
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 API ENDPOINTS FOR FRONTEND
// ═══════════════════════════════════════════════════════════════════════════════

// ✅ v16.0: مدل‌های آرشیو شده با فرمت مناسب Frontend
function apiGetArchivedModels() {
  try {
    const db = getArchivedModelsDB();
    const models = [];
    
    for (const [modelId, data] of Object.entries(db.models || {})) {
      if (data.archivedAt) {
        const modelInfo = MODEL_REGISTRY[modelId] || {};
        models.push({
          id: modelId,
          name: modelInfo.name || modelId,
          provider: modelInfo.provider || 'unknown',
          archivedAt: data.archivedAt,
          archiveReason: data.reason,
          errorCount: data.errorCount || 0,
          canRestore: data.canReactivate !== false
        });
      }
    }
    
    return { success: true, models: models };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

function apiArchiveModel(modelId, reason) { return archiveModelWithReason(modelId, reason || 'آرشیو دستی'); }
function apiReactivateModel(modelId) { return reactivateModel(modelId); }
function apiRestoreModel(modelId) { return reactivateModel(modelId); }  // Alias for frontend
function apiGetModelsReport() { return getModelsFullReport(); }
function apiSelectOptimalModel(projectType, task, complexity) { return selectOptimalModel(projectType, task, complexity); }

// ✅ v16.0: دریافت خلاصه عملکرد مدل‌ها
function apiGetModelsPerformanceSummary(projectId) {
  return getModelsPerformanceSummary(projectId);
}

// ✅ v16.0: ثبت امتیاز عملکرد مدل
function apiRecordModelPerformance(projectId, modelId, scores, taskType) {
  return recordModelPerformance(projectId, modelId, scores, taskType);
}

// پیام‌ها
function apiSendSmartMessage(projectId, message, attachments, options) {
  return sendSmartProjectMessage(projectId, message, attachments || [], options || {});
}

/**
 * ✅ v17.1.4: ذخیره مکالمه در context پروژه
 */
function apiSaveConversation(projectId, conversation) {
  try {
    if (!projectId || !conversation) {
      return { success: false, error: 'پارامترهای نامعتبر' };
    }
    
    const context = loadSmartProjectContext(projectId);
    if (!context) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    // اطمینان از وجود آرایه مکالمات
    if (!context.conversations) {
      context.conversations = [];
    }
    
    // اضافه کردن مکالمه جدید
    context.conversations.push({
      id: conversation.id || `conv_${Date.now()}`,
      userMessage: conversation.userMessage || '',
      aiResponse: conversation.aiResponse || '',
      model: conversation.model || 'AI',
      phase: context.currentPhase,
      timestamp: conversation.timestamp || new Date().toISOString()
    });
    
    // ✅ v17.1.5: به‌روزرسانی لیست مدل‌های فعال
    const modelId = conversation.model;
    if (modelId && modelId !== 'AI') {
      if (!context.models) {
        context.models = { active: [], scores: {}, primary: null, history: [] };
      }
      if (!context.models.active) context.models.active = [];
      if (!context.models.scores) context.models.scores = {};
      if (!context.models.history) context.models.history = [];
      
      // اضافه کردن مدل به لیست فعال‌ها اگر نباشد
      if (!context.models.active.includes(modelId)) {
        context.models.active.push(modelId);
      }
      
      // به‌روزرسانی امتیاز مدل
      if (!context.models.scores[modelId]) {
        context.models.scores[modelId] = { total: 0, count: 0, average: 75 };
      }
      context.models.scores[modelId].count++;
      context.models.scores[modelId].average = Math.min(100, context.models.scores[modelId].average + 0.5);
      
      // ثبت در تاریخچه مدل‌ها
      context.models.history.push({
        model: modelId,
        timestamp: new Date().toISOString(),
        action: 'responded'
      });
      
      // تنظیم مدل اصلی
      if (!context.models.primary) {
        context.models.primary = modelId;
      }
    }
    
    // اضافه کردن به تایم‌لاین
    if (!context.timeline) {
      context.timeline = [];
    }
    context.timeline.push({
      type: 'AI_INTERACTION',
      message: `مکالمه با ${conversation.model || 'AI'}: ${(conversation.userMessage || '').substring(0, 40)}...`,
      timestamp: new Date().toISOString()
    });
    
    // ✅ v17.1.5: به‌روزرسانی متریک‌ها
    if (!context.metrics) context.metrics = {};
    context.metrics.totalConversations = context.conversations.length;
    context.metrics.lastActivity = new Date().toISOString();
    
    // ذخیره
    saveSmartProjectContext(projectId, context);
    
    Logger.log('✅ مکالمه ذخیره شد: ' + projectId + ' با مدل: ' + modelId);
    
    return { success: true, conversationCount: context.conversations.length };
    
  } catch (error) {
    Logger.log('❌ خطا در ذخیره مکالمه: ' + error);
    return { success: false, error: error.message };
  }
}

// ✅ v17.1: تأیید پاسخ توسط مدل دوم
function apiValidateWithSecondModel(projectId, validationPrompt) {
  try {
    // انتخاب مدل دوم برای validation
    const models = getEnabledModels();
    const primaryModel = getCurrentModel();
    
    // انتخاب مدل متفاوت از مدل اصلی
    let validatorModel = models.find(m => m.id !== primaryModel && m.enabled);
    if (!validatorModel) {
      validatorModel = models[0]; // fallback
    }
    
    Logger.log('🔍 Validating with: ' + validatorModel?.id);
    
    // ارسال به مدل validator
    const response = callModelAPI(validatorModel.id, validationPrompt, {
      maxTokens: 2000,
      temperature: 0.3
    });
    
    if (!response || !response.success) {
      return { success: false, error: 'خطا در validation' };
    }
    
    // تلاش برای parse کردن JSON response
    let validationResult = {
      approved: true,
      score: 8,
      improvements: '',
      finalResponse: null
    };
    
    try {
      const responseText = response.response || response.content || '';
      
      // جستجوی JSON در پاسخ
      const jsonMatch = responseText.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0]);
        validationResult = {
          approved: parsed.approved !== false,
          score: parsed.score || 8,
          improvements: parsed.improvements || '',
          finalResponse: parsed.finalResponse || null
        };
      }
    } catch (parseError) {
      Logger.log('Could not parse validation JSON, using defaults');
    }
    
    return {
      success: true,
      model: validatorModel?.name || 'Validator',
      approved: validationResult.approved,
      score: validationResult.score,
      improvements: validationResult.improvements,
      finalResponse: validationResult.finalResponse
    };
    
  } catch (error) {
    Logger.log('❌ خطا در validation: ' + error);
    return { success: false, error: error.message };
  }
}

// ✅ v17.1: استخراج تسک‌ها از پاسخ AI
function apiExtractTasks(projectId, extractionPrompt) {
  try {
    // استفاده از یک مدل برای استخراج ساختار یافته
    const response = callModelAPI(getCurrentModel(), extractionPrompt, {
      maxTokens: 2000,
      temperature: 0.2 // دقت بالاتر
    });
    
    if (!response || !response.success) {
      return { success: false, error: 'خطا در استخراج', tasks: [] };
    }
    
    const responseText = response.response || response.content || '';
    
    // تلاش برای parse کردن آرایه JSON
    let tasks = [];
    
    try {
      // جستجوی آرایه JSON در پاسخ
      const arrayMatch = responseText.match(/\[[\s\S]*\]/);
      if (arrayMatch) {
        tasks = JSON.parse(arrayMatch[0]);
        
        // اعتبارسنجی ساختار تسک‌ها
        tasks = tasks.filter(t => t && typeof t === 'object' && t.name)
          .map(t => ({
            name: String(t.name).substring(0, 100),
            description: String(t.description || '').substring(0, 500),
            priority: ['high', 'medium', 'low'].includes(t.priority) ? t.priority : 'medium',
            estimatedDays: Math.min(Math.max(parseInt(t.estimatedDays) || 1, 1), 30),
            dependencies: Array.isArray(t.dependencies) ? t.dependencies : []
          }));
      }
    } catch (parseError) {
      Logger.log('Could not parse tasks JSON: ' + parseError);
    }
    
    Logger.log('📋 Extracted ' + tasks.length + ' tasks');
    
    return {
      success: true,
      tasks: tasks.slice(0, 15) // حداکثر 15 تسک
    };
    
  } catch (error) {
    Logger.log('❌ خطا در استخراج تسک‌ها: ' + error);
    return { success: false, error: error.message, tasks: [] };
  }
}

function apiSubmitLog(projectId, logContent, autoProgress) {
  return submitLogForAnalysis(projectId, logContent, autoProgress !== false);
}

// فایل‌ها
function apiUploadFile(projectId, fileName, content, mimeType) {
  return uploadFileToProject(projectId, fileName, content, mimeType);
}

function apiProcessZip(projectId, fileId) {
  return processZipFileInProject(projectId, fileId);
}

// ژورنال
function apiGetJournal(options) { return getJournalEntries(options || {}); }

// پروژه هوشمند
function apiSmartCreateProject(prompt, attachments) {
  return createSmartProjectFromPrompt(prompt, attachments || []);
}

// ═══════════════════════════════════════════════════════════════════════════════
// ✅ v16.0: PHASE 3 - DYNAMIC TREE DIAGRAM APIs
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * دریافت ساختار درختی پروژه برای نمایش
 */
function apiGetProjectTree(projectId) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    const phases = context.phases || [];
    const currentPhase = context.currentPhase;
    
    // ساخت ساختار درختی
    const tree = {
      projectId: projectId,
      projectName: context.project.name,
      totalPhases: phases.length,
      completedPhases: phases.filter(p => p.status === 'completed').length,
      currentPhaseIndex: phases.findIndex(p => p.id === currentPhase?.id),
      phases: phases.map((phase, index) => {
        const statusConfig = PERSISTENT_PROJECT_CONFIG.PHASE_STATUS[phase.status?.toUpperCase()] || 
                            PERSISTENT_PROJECT_CONFIG.PHASE_STATUS.PENDING;
        return {
          id: phase.id,
          index: index,
          name: phase.name,
          description: phase.description || '',
          status: phase.status || 'pending',
          statusLabel: statusConfig.label,
          statusColor: statusConfig.color,
          statusIcon: statusConfig.icon,
          progress: phase.progress || 0,
          isCurrent: phase.id === currentPhase?.id,
          startedAt: phase.startedAt || null,
          completedAt: phase.completedAt || null,
          files: phase.files || [],
          notes: phase.notes || [],
          outputs: phase.outputs || []
        };
      }),
      config: PERSISTENT_PROJECT_CONFIG.TREE_DIAGRAM
    };
    
    return { success: true, tree: tree };
  } catch (error) {
    Logger.log('❌ خطا در دریافت ساختار درختی: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * به‌روزرسانی وضعیت یک فاز
 */
function apiUpdatePhaseStatus(projectId, phaseIndex, newStatus, notes) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context || !context.phases || !context.phases[phaseIndex]) {
      return { success: false, error: 'فاز یافت نشد' };
    }
    
    const phase = context.phases[phaseIndex];
    const oldStatus = phase.status;
    
    // به‌روزرسانی وضعیت
    phase.status = newStatus;
    phase.updatedAt = new Date().toISOString();
    
    // تنظیم تاریخ‌ها
    if (newStatus === 'in_progress' && !phase.startedAt) {
      phase.startedAt = new Date().toISOString();
    } else if (newStatus === 'completed') {
      phase.completedAt = new Date().toISOString();
      phase.progress = 100;
    }
    
    // اضافه کردن یادداشت
    if (notes) {
      phase.notes = phase.notes || [];
      phase.notes.push({
        text: notes,
        timestamp: new Date().toISOString(),
        type: 'status_change',
        oldStatus: oldStatus,
        newStatus: newStatus
      });
    }
    
    // ذخیره
    saveSmartProjectContext(projectId, context);
    
    // ثبت در ژورنال
    logToJournal('phase_status_changed', 'project', {
      projectId,
      phaseIndex,
      phaseName: phase.name,
      oldStatus,
      newStatus,
      notes
    });
    
    Logger.log(`✅ وضعیت فاز "${phase.name}" از ${oldStatus} به ${newStatus} تغییر کرد`);
    
    return { 
      success: true, 
      phase: phase,
      message: `وضعیت فاز "${phase.name}" به‌روز شد`
    };
  } catch (error) {
    Logger.log('❌ خطا در به‌روزرسانی وضعیت فاز: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * به‌روزرسانی پیشرفت یک فاز
 */
function apiUpdatePhaseProgress(projectId, phaseIndex, progress) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context || !context.phases || !context.phases[phaseIndex]) {
      return { success: false, error: 'فاز یافت نشد' };
    }
    
    const phase = context.phases[phaseIndex];
    phase.progress = Math.min(100, Math.max(0, parseInt(progress) || 0));
    phase.updatedAt = new Date().toISOString();
    
    // اگر پیشرفت ۱۰۰٪ شد، وضعیت را تکمیل کن
    if (phase.progress === 100 && phase.status !== 'completed') {
      phase.status = 'completed';
      phase.completedAt = new Date().toISOString();
    }
    
    saveSmartProjectContext(projectId, context);
    
    return { 
      success: true, 
      phase: phase,
      message: `پیشرفت فاز "${phase.name}": ${phase.progress}%`
    };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * حرکت به فاز بعدی
 */
function apiMoveToNextPhase(projectId, autoComplete) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context || !context.phases) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    const currentIndex = context.phases.findIndex(p => p.id === context.currentPhase?.id);
    
    // تکمیل فاز فعلی اگر خواسته شده
    if (autoComplete && currentIndex >= 0) {
      context.phases[currentIndex].status = 'completed';
      context.phases[currentIndex].progress = 100;
      context.phases[currentIndex].completedAt = new Date().toISOString();
    }
    
    // حرکت به فاز بعدی
    const nextIndex = currentIndex + 1;
    if (nextIndex < context.phases.length) {
      context.currentPhase = context.phases[nextIndex];
      context.phases[nextIndex].status = 'in_progress';
      context.phases[nextIndex].startedAt = new Date().toISOString();
      
      saveSmartProjectContext(projectId, context);
      
      return { 
        success: true, 
        currentPhase: context.currentPhase,
        message: `حرکت به فاز "${context.currentPhase.name}"`
      };
    } else {
      return { 
        success: true, 
        completed: true,
        message: 'تمام فازها تکمیل شدند!'
      };
    }
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * برگشت به فاز قبلی
 */
function apiMoveToPreviousPhase(projectId) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context || !context.phases) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    const currentIndex = context.phases.findIndex(p => p.id === context.currentPhase?.id);
    
    if (currentIndex > 0) {
      // علامت‌گذاری فاز فعلی به عنوان برگشت
      context.phases[currentIndex].status = 'rollback';
      
      // برگشت به فاز قبلی
      const prevIndex = currentIndex - 1;
      context.currentPhase = context.phases[prevIndex];
      context.phases[prevIndex].status = 'in_progress';
      
      saveSmartProjectContext(projectId, context);
      
      return { 
        success: true, 
        currentPhase: context.currentPhase,
        message: `برگشت به فاز "${context.currentPhase.name}"`
      };
    } else {
      return { success: false, error: 'در اولین فاز هستید' };
    }
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 END OF SMART PROJECT SYSTEM
// ═══════════════════════════════════════════════════════════════════════════════
// ═══════════════════════════════════════════════════════════════════════════════
// ╔═══════════════════════════════════════════════════════════════════════════════╗
// ║  🧠 اتاق فکر مهندسی هوشمند - فاز ۱                                            ║
// ║  نسخه: 17.0 - SMART ENGINEERING THINK TANK                                    ║
// ╠═══════════════════════════════════════════════════════════════════════════════╣
// ║  ✅ تحلیل پروژه‌های خارجی (Google Console, GitHub, etc)                       ║
// ║  ✅ تولید خودکار نمودار Mermaid از ساختار کد                                  ║
// ║  ✅ دستورات اجرایی گام‌به‌گام با قالب استاندارد و اعتبارسنجی                  ║
// ║  ✅ مکانیزم بازخورد از اجرای دستورات                                          ║
// ╚═══════════════════════════════════════════════════════════════════════════════╝

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 1: EXTERNAL PROJECT ANALYSIS SYSTEM
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0: تنظیمات سیستم تحلیل پروژه خارجی
 */
const EXTERNAL_PROJECT_CONFIG = {
  // انواع پلتفرم‌های پشتیبانی شده
  PLATFORMS: {
    GOOGLE_CONSOLE: { id: 'google_console', label: 'Google Cloud Console', icon: '☁️' },
    GOOGLE_APPS_SCRIPT: { id: 'google_apps_script', label: 'Google Apps Script', icon: '📜' },
    GITHUB: { id: 'github', label: 'GitHub', icon: '🐙' },
    LOCAL: { id: 'local', label: 'پروژه محلی', icon: '💻' },
    OTHER: { id: 'other', label: 'سایر', icon: '📁' }
  },
  
  // الگوهای تشخیص نوع فایل
  FILE_PATTERNS: {
    BACKEND: {
      patterns: ['backend', 'server', 'api', 'controller', 'service', 'model', 'route', '.gs'],
      icon: '⚙️',
      color: '#4CAF50'
    },
    FRONTEND: {
      patterns: ['frontend', 'client', 'view', 'component', 'page', 'ui', 'index.html', '.jsx', '.tsx', '.vue'],
      icon: '🎨',
      color: '#2196F3'
    },
    CONFIG: {
      patterns: ['config', 'setting', '.env', '.json', 'manifest', 'package.json', 'appsscript.json'],
      icon: '⚙️',
      color: '#FF9800'
    },
    DATABASE: {
      patterns: ['database', 'db', 'schema', 'migration', 'model', '.sql'],
      icon: '🗄️',
      color: '#9C27B0'
    },
    TEST: {
      patterns: ['test', 'spec', '__test__', '.test.', '.spec.'],
      icon: '🧪',
      color: '#00BCD4'
    },
    DOCS: {
      patterns: ['readme', 'doc', 'guide', 'manual', '.md', 'changelog'],
      icon: '📄',
      color: '#607D8B'
    }
  },
  
  // تنظیمات تحلیل
  ANALYSIS: {
    MAX_FILE_SIZE: 500000, // 500KB
    MAX_FILES: 50,
    EXTRACT_FUNCTIONS: true,
    EXTRACT_CLASSES: true,
    EXTRACT_IMPORTS: true,
    EXTRACT_EXPORTS: true,
    DETECT_PATTERNS: true
  }
};

/**
 * ✅ v17.0: تحلیل کامل پروژه خارجی
 * @param {Array} files - فایل‌های پروژه
 * @param {Object} metadata - اطلاعات اضافی (پلتفرم، تاریخچه، چالش‌ها)
 * @returns {Object} - نتیجه تحلیل جامع
 */
function analyzeExternalProject(files, metadata = {}) {
  try {
    Logger.log('🧠 شروع تحلیل پروژه خارجی...');
    
    const analysis = {
      timestamp: new Date().toISOString(),
      platform: metadata.platform || detectPlatform(files),
      overview: {
        totalFiles: 0,
        totalLines: 0,
        languages: {},
        fileTypes: {}
      },
      architecture: {
        layers: [],
        components: [],
        dependencies: []
      },
      codeAnalysis: {
        functions: [],
        classes: [],
        imports: [],
        exports: [],
        patterns: []
      },
      issues: {
        bugs: [],
        warnings: [],
        suggestions: []
      },
      roadmap: {
        currentStage: '',
        completedTasks: [],
        pendingTasks: [],
        suggestedNextSteps: []
      },
      diagrams: {
        architecture: '',
        dataFlow: '',
        componentTree: ''
      }
    };
    
    // ۱. پردازش هر فایل
    for (const file of files) {
      if (!file || !file.content) continue;
      
      analysis.overview.totalFiles++;
      const lines = (file.content.match(/\n/g) || []).length + 1;
      analysis.overview.totalLines += lines;
      
      // تشخیص زبان و نوع فایل
      const fileInfo = detectFileInfo(file.name, file.content);
      analysis.overview.languages[fileInfo.language] = (analysis.overview.languages[fileInfo.language] || 0) + 1;
      analysis.overview.fileTypes[fileInfo.type] = (analysis.overview.fileTypes[fileInfo.type] || 0) + 1;
      
      // استخراج ساختار کد
      if (EXTERNAL_PROJECT_CONFIG.ANALYSIS.EXTRACT_FUNCTIONS) {
        const funcs = extractFunctions(file.content, fileInfo.language);
        analysis.codeAnalysis.functions.push(...funcs.map(f => ({ ...f, file: file.name })));
      }
      
      if (EXTERNAL_PROJECT_CONFIG.ANALYSIS.EXTRACT_CLASSES) {
        const classes = extractClasses(file.content, fileInfo.language);
        analysis.codeAnalysis.classes.push(...classes.map(c => ({ ...c, file: file.name })));
      }
      
      if (EXTERNAL_PROJECT_CONFIG.ANALYSIS.EXTRACT_IMPORTS) {
        const imports = extractImports(file.content, fileInfo.language);
        analysis.codeAnalysis.imports.push(...imports.map(i => ({ ...i, file: file.name })));
      }
      
      // تشخیص مشکلات
      const issues = detectIssues(file.content, file.name);
      analysis.issues.bugs.push(...issues.bugs);
      analysis.issues.warnings.push(...issues.warnings);
      analysis.issues.suggestions.push(...issues.suggestions);
    }
    
    // ۲. تحلیل معماری
    analysis.architecture = analyzeArchitecture(files, analysis.codeAnalysis);
    
    // ۳. تشخیص مرحله فعلی پروژه
    analysis.roadmap = detectProjectStage(analysis);
    
    // ۴. تولید نمودارها
    analysis.diagrams.architecture = generateArchitectureDiagram(analysis);
    analysis.diagrams.dataFlow = generateDataFlowDiagram(analysis);
    analysis.diagrams.componentTree = generateComponentTreeDiagram(analysis);
    
    // ۵. تولید گزارش خلاصه
    analysis.summary = generateAnalysisSummary(analysis, metadata);
    
    Logger.log('✅ تحلیل پروژه کامل شد');
    
    return {
      success: true,
      analysis: analysis
    };
    
  } catch (error) {
    Logger.log('❌ خطا در تحلیل پروژه: ' + error);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * ✅ v17.0: تشخیص پلتفرم از روی فایل‌ها
 */
function detectPlatform(files) {
  const fileNames = files.map(f => (f.name || '').toLowerCase());
  
  // Google Apps Script
  if (fileNames.some(f => f.endsWith('.gs') || f === 'appsscript.json')) {
    return EXTERNAL_PROJECT_CONFIG.PLATFORMS.GOOGLE_APPS_SCRIPT;
  }
  
  // Google Cloud
  if (fileNames.some(f => f.includes('app.yaml') || f.includes('cloudbuild') || f.includes('gcloud'))) {
    return EXTERNAL_PROJECT_CONFIG.PLATFORMS.GOOGLE_CONSOLE;
  }
  
  // GitHub
  if (fileNames.some(f => f.includes('.github') || f === '.gitignore')) {
    return EXTERNAL_PROJECT_CONFIG.PLATFORMS.GITHUB;
  }
  
  return EXTERNAL_PROJECT_CONFIG.PLATFORMS.LOCAL;
}

/**
 * ✅ v17.0: تشخیص اطلاعات فایل
 */
function detectFileInfo(fileName, content) {
  const ext = (fileName || '').split('.').pop().toLowerCase();
  
  const languageMap = {
    'js': 'JavaScript', 'jsx': 'JavaScript/React', 'ts': 'TypeScript', 'tsx': 'TypeScript/React',
    'gs': 'Google Apps Script', 'py': 'Python', 'java': 'Java', 'kt': 'Kotlin',
    'html': 'HTML', 'css': 'CSS', 'scss': 'SCSS', 'vue': 'Vue',
    'json': 'JSON', 'xml': 'XML', 'yaml': 'YAML', 'yml': 'YAML',
    'sql': 'SQL', 'sh': 'Shell', 'md': 'Markdown'
  };
  
  let type = 'OTHER';
  const lowerName = fileName.toLowerCase();
  
  for (const [key, config] of Object.entries(EXTERNAL_PROJECT_CONFIG.FILE_PATTERNS)) {
    if (config.patterns.some(p => lowerName.includes(p))) {
      type = key;
      break;
    }
  }
  
  return {
    language: languageMap[ext] || 'Unknown',
    extension: ext,
    type: type,
    icon: EXTERNAL_PROJECT_CONFIG.FILE_PATTERNS[type]?.icon || '📄'
  };
}

/**
 * ✅ v17.0: استخراج توابع از کد
 */
function extractFunctions(content, language) {
  const functions = [];
  
  // JavaScript/TypeScript/Google Apps Script patterns
  const jsPatterns = [
    /function\s+(\w+)\s*\(([^)]*)\)/g,
    /const\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>/g,
    /(\w+)\s*:\s*(?:async\s*)?function\s*\(([^)]*)\)/g,
    /(?:async\s+)?(\w+)\s*\(([^)]*)\)\s*\{/g
  ];
  
  // Python patterns
  const pyPatterns = [
    /def\s+(\w+)\s*\(([^)]*)\)/g,
    /async\s+def\s+(\w+)\s*\(([^)]*)\)/g
  ];
  
  const patterns = ['JavaScript', 'TypeScript', 'Google Apps Script', 'JavaScript/React', 'TypeScript/React']
    .includes(language) ? jsPatterns : language === 'Python' ? pyPatterns : jsPatterns;
  
  for (const pattern of patterns) {
    let match;
    while ((match = pattern.exec(content)) !== null) {
      const funcName = match[1];
      // فیلتر کلمات کلیدی
      if (!['if', 'for', 'while', 'switch', 'catch', 'return', 'function'].includes(funcName)) {
        functions.push({
          name: funcName,
          params: match[2] || '',
          line: content.substring(0, match.index).split('\n').length
        });
      }
    }
  }
  
  // حذف تکراری‌ها
  const unique = [];
  const seen = new Set();
  for (const f of functions) {
    const key = f.name + ':' + f.line;
    if (!seen.has(key)) {
      seen.add(key);
      unique.push(f);
    }
  }
  
  return unique;
}

/**
 * ✅ v17.0: استخراج کلاس‌ها از کد
 */
function extractClasses(content, language) {
  const classes = [];
  
  // JavaScript/TypeScript class pattern
  const jsClassPattern = /class\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{/g;
  
  let match;
  while ((match = jsClassPattern.exec(content)) !== null) {
    classes.push({
      name: match[1],
      extends: match[2] || null,
      line: content.substring(0, match.index).split('\n').length
    });
  }
  
  return classes;
}

/**
 * ✅ v17.0: استخراج importها از کد
 */
function extractImports(content, language) {
  const imports = [];
  
  // JavaScript/TypeScript import patterns
  const patterns = [
    /import\s+(?:{[^}]+}|\w+|\*\s+as\s+\w+)\s+from\s+['"]([^'"]+)['"]/g,
    /require\s*\(['"]([^'"]+)['"]\)/g
  ];
  
  for (const pattern of patterns) {
    let match;
    while ((match = pattern.exec(content)) !== null) {
      imports.push({
        module: match[1],
        line: content.substring(0, match.index).split('\n').length
      });
    }
  }
  
  return imports;
}

/**
 * ✅ v17.0: تشخیص مشکلات کد
 */
function detectIssues(content, fileName) {
  const issues = {
    bugs: [],
    warnings: [],
    suggestions: []
  };
  
  const lines = content.split('\n');
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const lineNum = i + 1;
    
    // تشخیص TODO و FIXME
    if (/\/\/\s*(TODO|FIXME|BUG|HACK)/i.test(line)) {
      const match = line.match(/\/\/\s*(TODO|FIXME|BUG|HACK)\s*:?\s*(.*)/i);
      if (match) {
        const type = match[1].toUpperCase();
        const message = match[2] || '';
        
        if (type === 'BUG' || type === 'FIXME') {
          issues.bugs.push({ file: fileName, line: lineNum, message: message, type: type });
        } else {
          issues.warnings.push({ file: fileName, line: lineNum, message: message, type: type });
        }
      }
    }
    
    // تشخیص console.log در کد
    if (/console\.(log|error|warn)\s*\(/.test(line) && !fileName.includes('test')) {
      issues.suggestions.push({
        file: fileName,
        line: lineNum,
        message: 'حذف console.log قبل از production',
        type: 'CLEANUP'
      });
    }
    
    // تشخیص try بدون catch
    if (/try\s*\{/.test(line)) {
      // بررسی ساده - می‌توان بهبود داد
      const nextLines = lines.slice(i + 1, i + 20).join('\n');
      if (!nextLines.includes('catch')) {
        issues.warnings.push({
          file: fileName,
          line: lineNum,
          message: 'احتمال عدم وجود catch برای try',
          type: 'ERROR_HANDLING'
        });
      }
    }
    
    // تشخیص hardcoded credentials
    if (/(['"])[A-Za-z0-9_-]{20,}\1/.test(line) && 
        (line.toLowerCase().includes('key') || line.toLowerCase().includes('secret') || line.toLowerCase().includes('password'))) {
      issues.bugs.push({
        file: fileName,
        line: lineNum,
        message: 'احتمال وجود credential در کد - از Script Properties استفاده کنید',
        type: 'SECURITY'
      });
    }
  }
  
  return issues;
}

/**
 * ✅ v17.0: تحلیل معماری پروژه
 */
function analyzeArchitecture(files, codeAnalysis) {
  const architecture = {
    layers: [],
    components: [],
    dependencies: []
  };
  
  // تشخیص لایه‌ها
  const layerMap = {
    FRONTEND: { files: [], functions: 0 },
    BACKEND: { files: [], functions: 0 },
    DATABASE: { files: [], functions: 0 },
    CONFIG: { files: [], functions: 0 },
    TEST: { files: [], functions: 0 }
  };
  
  for (const file of files) {
    const fileInfo = detectFileInfo(file.name, file.content || '');
    if (layerMap[fileInfo.type]) {
      layerMap[fileInfo.type].files.push(file.name);
    }
  }
  
  // شمارش توابع هر لایه
  for (const func of codeAnalysis.functions) {
    for (const [layer, data] of Object.entries(layerMap)) {
      if (data.files.some(f => func.file.includes(f) || f.includes(func.file))) {
        data.functions++;
      }
    }
  }
  
  // ساخت لیست لایه‌ها
  for (const [name, data] of Object.entries(layerMap)) {
    if (data.files.length > 0) {
      architecture.layers.push({
        name: name,
        fileCount: data.files.length,
        functionCount: data.functions,
        files: data.files
      });
    }
  }
  
  // تشخیص کامپوننت‌ها از توابع اصلی
  const mainFunctions = codeAnalysis.functions.filter(f => 
    f.name.startsWith('get') || f.name.startsWith('set') || 
    f.name.startsWith('create') || f.name.startsWith('update') ||
    f.name.startsWith('delete') || f.name.startsWith('handle') ||
    f.name.startsWith('api') || f.name.startsWith('process')
  );
  
  // گروه‌بندی بر اساس پیشوند
  const componentGroups = {};
  for (const func of mainFunctions) {
    const prefix = func.name.match(/^(get|set|create|update|delete|handle|api|process)/)?.[0] || 'other';
    if (!componentGroups[prefix]) {
      componentGroups[prefix] = [];
    }
    componentGroups[prefix].push(func);
  }
  
  for (const [prefix, funcs] of Object.entries(componentGroups)) {
    architecture.components.push({
      name: prefix.charAt(0).toUpperCase() + prefix.slice(1) + ' Operations',
      functions: funcs.map(f => f.name),
      type: prefix
    });
  }
  
  // تشخیص وابستگی‌ها
  const moduleGroups = {};
  for (const imp of codeAnalysis.imports) {
    if (!moduleGroups[imp.module]) {
      moduleGroups[imp.module] = [];
    }
    moduleGroups[imp.module].push(imp.file);
  }
  
  for (const [module, files] of Object.entries(moduleGroups)) {
    architecture.dependencies.push({
      module: module,
      usedBy: files,
      type: module.startsWith('.') ? 'internal' : 'external'
    });
  }
  
  return architecture;
}

/**
 * ✅ v17.0: تشخیص مرحله فعلی پروژه
 */
function detectProjectStage(analysis) {
  const roadmap = {
    currentStage: 'unknown',
    completedTasks: [],
    pendingTasks: [],
    suggestedNextSteps: [],
    progress: 0
  };
  
  const indicators = {
    hasBackend: analysis.architecture.layers.some(l => l.name === 'BACKEND'),
    hasFrontend: analysis.architecture.layers.some(l => l.name === 'FRONTEND'),
    hasTests: analysis.architecture.layers.some(l => l.name === 'TEST'),
    hasConfig: analysis.architecture.layers.some(l => l.name === 'CONFIG'),
    bugCount: analysis.issues.bugs.length,
    warningCount: analysis.issues.warnings.length,
    functionCount: analysis.codeAnalysis.functions.length,
    totalLines: analysis.overview.totalLines
  };
  
  // تشخیص مرحله
  if (indicators.totalLines < 500) {
    roadmap.currentStage = 'شروع پروژه';
    roadmap.progress = 10;
    roadmap.suggestedNextSteps = [
      'تعریف معماری کلی',
      'ایجاد ساختار فولدری',
      'پیاده‌سازی توابع اصلی'
    ];
  } else if (!indicators.hasTests && indicators.functionCount > 10) {
    roadmap.currentStage = 'پیاده‌سازی اولیه';
    roadmap.progress = 40;
    roadmap.suggestedNextSteps = [
      'اضافه کردن تست‌ها',
      'مستندسازی توابع',
      'رفع باگ‌های شناسایی شده'
    ];
  } else if (indicators.bugCount > 5) {
    roadmap.currentStage = 'رفع اشکال';
    roadmap.progress = 60;
    roadmap.suggestedNextSteps = [
      `رفع ${indicators.bugCount} باگ شناسایی شده`,
      'بررسی warning ها',
      'تست مجدد'
    ];
  } else if (indicators.hasTests && indicators.bugCount < 3) {
    roadmap.currentStage = 'آماده استقرار';
    roadmap.progress = 85;
    roadmap.suggestedNextSteps = [
      'تست نهایی',
      'آماده‌سازی محیط production',
      'استقرار'
    ];
  } else {
    roadmap.currentStage = 'توسعه فعال';
    roadmap.progress = 50;
  }
  
  // تسک‌های تکمیل شده
  if (indicators.hasBackend) roadmap.completedTasks.push('پیاده‌سازی Backend');
  if (indicators.hasFrontend) roadmap.completedTasks.push('پیاده‌سازی Frontend');
  if (indicators.hasConfig) roadmap.completedTasks.push('تنظیمات پروژه');
  if (indicators.hasTests) roadmap.completedTasks.push('نوشتن تست‌ها');
  
  // تسک‌های باقیمانده
  if (!indicators.hasTests) roadmap.pendingTasks.push('نوشتن Unit Tests');
  if (indicators.bugCount > 0) roadmap.pendingTasks.push(`رفع ${indicators.bugCount} باگ`);
  if (indicators.warningCount > 0) roadmap.pendingTasks.push(`بررسی ${indicators.warningCount} هشدار`);
  
  return roadmap;
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 2: MERMAID DIAGRAM GENERATION
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0: تولید نمودار معماری Mermaid
 */
function generateArchitectureDiagram(analysis) {
  let mermaid = 'graph TB\n';
  mermaid += '  subgraph "🏗️ معماری سیستم"\n';
  
  // اضافه کردن لایه‌ها
  const layerColors = {
    FRONTEND: '#e3f2fd',
    BACKEND: '#e8f5e9',
    DATABASE: '#f3e5f5',
    CONFIG: '#fff3e0',
    TEST: '#e0f7fa'
  };
  
  for (const layer of analysis.architecture.layers) {
    const color = layerColors[layer.name] || '#f5f5f5';
    mermaid += `    ${layer.name}["${getLayerIcon(layer.name)} ${layer.name}<br/>${layer.fileCount} فایل | ${layer.functionCount} تابع"]\n`;
  }
  
  // اضافه کردن اتصالات
  if (analysis.architecture.layers.some(l => l.name === 'FRONTEND') && 
      analysis.architecture.layers.some(l => l.name === 'BACKEND')) {
    mermaid += '    FRONTEND -->|API Calls| BACKEND\n';
  }
  
  if (analysis.architecture.layers.some(l => l.name === 'BACKEND') && 
      analysis.architecture.layers.some(l => l.name === 'DATABASE')) {
    mermaid += '    BACKEND -->|Data| DATABASE\n';
  }
  
  if (analysis.architecture.layers.some(l => l.name === 'CONFIG')) {
    mermaid += '    CONFIG -.->|Settings| BACKEND\n';
    if (analysis.architecture.layers.some(l => l.name === 'FRONTEND')) {
      mermaid += '    CONFIG -.->|Settings| FRONTEND\n';
    }
  }
  
  if (analysis.architecture.layers.some(l => l.name === 'TEST')) {
    mermaid += '    TEST -.->|Tests| BACKEND\n';
  }
  
  mermaid += '  end\n';
  
  // استایل‌ها
  mermaid += '\n  %% Styling\n';
  for (const layer of analysis.architecture.layers) {
    const color = layerColors[layer.name] || '#f5f5f5';
    mermaid += `  style ${layer.name} fill:${color},stroke:#333,stroke-width:2px\n`;
  }
  
  return mermaid;
}

/**
 * ✅ v17.0: آیکون لایه
 */
function getLayerIcon(layer) {
  const icons = {
    FRONTEND: '🎨',
    BACKEND: '⚙️',
    DATABASE: '🗄️',
    CONFIG: '⚡',
    TEST: '🧪'
  };
  return icons[layer] || '📁';
}

/**
 * ✅ v17.0: تولید نمودار جریان داده Mermaid
 */
function generateDataFlowDiagram(analysis) {
  let mermaid = 'flowchart LR\n';
  mermaid += '  subgraph "📊 جریان داده"\n';
  
  // ایجاد نودها برای کامپوننت‌های اصلی
  mermaid += '    USER([👤 کاربر])\n';
  
  if (analysis.architecture.layers.some(l => l.name === 'FRONTEND')) {
    mermaid += '    UI[🎨 رابط کاربری]\n';
  }
  
  if (analysis.architecture.layers.some(l => l.name === 'BACKEND')) {
    mermaid += '    API[⚙️ API/Backend]\n';
  }
  
  if (analysis.architecture.layers.some(l => l.name === 'DATABASE')) {
    mermaid += '    DB[(🗄️ پایگاه داده)]\n';
  }
  
  // تشخیص سرویس‌های خارجی از imports
  const externalServices = analysis.architecture.dependencies
    .filter(d => d.type === 'external')
    .slice(0, 5);
  
  if (externalServices.length > 0) {
    mermaid += '    EXT[☁️ سرویس‌های خارجی]\n';
  }
  
  mermaid += '  end\n\n';
  
  // اتصالات
  mermaid += '  %% Data Flow\n';
  
  if (analysis.architecture.layers.some(l => l.name === 'FRONTEND')) {
    mermaid += '  USER --> UI\n';
    if (analysis.architecture.layers.some(l => l.name === 'BACKEND')) {
      mermaid += '  UI <--> API\n';
    }
  } else if (analysis.architecture.layers.some(l => l.name === 'BACKEND')) {
    mermaid += '  USER --> API\n';
  }
  
  if (analysis.architecture.layers.some(l => l.name === 'BACKEND') && 
      analysis.architecture.layers.some(l => l.name === 'DATABASE')) {
    mermaid += '  API <--> DB\n';
  }
  
  if (externalServices.length > 0 && analysis.architecture.layers.some(l => l.name === 'BACKEND')) {
    mermaid += '  API <--> EXT\n';
  }
  
  return mermaid;
}

/**
 * ✅ v17.0: تولید نمودار درختی کامپوننت‌ها
 */
function generateComponentTreeDiagram(analysis) {
  let mermaid = 'graph TD\n';
  mermaid += '  ROOT["🏠 پروژه"]\n';
  
  // اضافه کردن فایل‌ها به صورت گروه‌بندی شده
  for (const layer of analysis.architecture.layers) {
    const layerId = layer.name;
    const icon = getLayerIcon(layer.name);
    mermaid += `  ROOT --> ${layerId}["${icon} ${layer.name}"]\n`;
    
    // اضافه کردن فایل‌های هر لایه (حداکثر ۵ تا)
    const filesToShow = layer.files.slice(0, 5);
    filesToShow.forEach((file, idx) => {
      const fileId = `${layerId}_F${idx}`;
      const shortName = file.length > 20 ? file.substring(0, 17) + '...' : file;
      mermaid += `  ${layerId} --> ${fileId}["📄 ${shortName}"]\n`;
    });
    
    if (layer.files.length > 5) {
      mermaid += `  ${layerId} --> ${layerId}_MORE["... +${layer.files.length - 5} فایل دیگر"]\n`;
    }
  }
  
  return mermaid;
}

/**
 * ✅ v17.0: تولید گزارش خلاصه تحلیل
 */
function generateAnalysisSummary(analysis, metadata) {
  let summary = `# 📊 گزارش تحلیل پروژه\n\n`;
  
  // اطلاعات کلی
  summary += `## 📌 اطلاعات کلی\n`;
  summary += `- **پلتفرم:** ${analysis.platform.label || 'نامشخص'}\n`;
  summary += `- **تعداد فایل‌ها:** ${analysis.overview.totalFiles}\n`;
  summary += `- **مجموع خطوط:** ${analysis.overview.totalLines.toLocaleString()}\n`;
  summary += `- **زبان‌ها:** ${Object.keys(analysis.overview.languages).join(', ')}\n\n`;
  
  // وضعیت فعلی
  summary += `## 🎯 وضعیت فعلی\n`;
  summary += `- **مرحله:** ${analysis.roadmap.currentStage}\n`;
  summary += `- **پیشرفت:** ${analysis.roadmap.progress}%\n\n`;
  
  // مشکلات
  if (analysis.issues.bugs.length > 0 || analysis.issues.warnings.length > 0) {
    summary += `## ⚠️ مشکلات شناسایی شده\n`;
    summary += `- **باگ‌ها:** ${analysis.issues.bugs.length}\n`;
    summary += `- **هشدارها:** ${analysis.issues.warnings.length}\n`;
    summary += `- **پیشنهادات:** ${analysis.issues.suggestions.length}\n\n`;
  }
  
  // گام‌های بعدی
  summary += `## 🚀 گام‌های پیشنهادی بعدی\n`;
  for (const step of analysis.roadmap.suggestedNextSteps) {
    summary += `- ${step}\n`;
  }
  
  return summary;
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 3: EXECUTABLE COMMANDS SYSTEM
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0: تنظیمات سیستم دستورات اجرایی
 */
const COMMAND_SYSTEM_CONFIG = {
  // انواع محیط اجرا
  ENVIRONMENTS: {
    TERMINAL: { id: 'terminal', label: 'Terminal', icon: '💻' },
    CLOUD_SHELL: { id: 'cloud_shell', label: 'Google Cloud Shell', icon: '☁️' },
    APPS_SCRIPT: { id: 'apps_script', label: 'Apps Script Editor', icon: '📜' },
    BROWSER: { id: 'browser', label: 'Browser Console', icon: '🌐' }
  },
  
  // قالب دستورات
  COMMAND_TEMPLATE: {
    step: 0,
    phase: '',
    task: '',
    command: '',
    params: [],
    expectedOutput: '',
    validation: '',
    nextStep: '',
    rollback: '',
    notes: []
  }
};

/**
 * ✅ v17.0: تولید دستورات اجرایی برای یک مرحله
 * @param {string} projectId - شناسه پروژه
 * @param {Object} context - اطلاعات پروژه
 * @returns {Object} - دستورات اجرایی
 */
function generateExecutableCommands(projectId, context) {
  try {
    Logger.log('📋 تولید دستورات اجرایی برای پروژه: ' + projectId);
    
    const commands = {
      projectId: projectId,
      timestamp: new Date().toISOString(),
      currentPhase: context.currentPhase?.name || 'نامشخص',
      steps: [],
      environment: detectCommandEnvironment(context)
    };
    
    // تولید دستورات بر اساس نوع پروژه و مرحله
    const projectType = context.project?.type || 'coding';
    const currentPhase = context.currentPhase?.name || '';
    
    // دستورات عمومی برای هر مرحله
    const commonSteps = generateCommonCommands(context);
    commands.steps.push(...commonSteps);
    
    // دستورات خاص بر اساس مرحله
    const phaseSteps = generatePhaseSpecificCommands(projectType, currentPhase, context);
    commands.steps.push(...phaseSteps);
    
    // شماره‌گذاری مجدد
    commands.steps.forEach((step, idx) => {
      step.step = idx + 1;
    });
    
    Logger.log(`✅ ${commands.steps.length} دستور تولید شد`);
    
    return {
      success: true,
      commands: commands
    };
    
  } catch (error) {
    Logger.log('❌ خطا در تولید دستورات: ' + error);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * ✅ v17.0: تشخیص محیط اجرای دستورات
 */
function detectCommandEnvironment(context) {
  const platform = context.platform?.id || context.project?.platform || '';
  
  if (platform.includes('google_apps_script') || platform.includes('gs')) {
    return COMMAND_SYSTEM_CONFIG.ENVIRONMENTS.APPS_SCRIPT;
  }
  
  if (platform.includes('google_console') || platform.includes('gcloud')) {
    return COMMAND_SYSTEM_CONFIG.ENVIRONMENTS.CLOUD_SHELL;
  }
  
  return COMMAND_SYSTEM_CONFIG.ENVIRONMENTS.TERMINAL;
}

/**
 * ✅ v17.0: تولید دستورات عمومی
 */
function generateCommonCommands(context) {
  const commands = [];
  const env = detectCommandEnvironment(context);
  
  // دستور بررسی وضعیت
  if (env.id === 'cloud_shell') {
    commands.push({
      phase: 'آماده‌سازی',
      task: 'بررسی محیط Cloud Shell',
      command: 'gcloud info',
      params: [],
      expectedOutput: 'نمایش اطلاعات حساب و پروژه فعال',
      validation: 'اگر Account و Project نمایش داده شد، محیط آماده است',
      nextStep: 'ادامه به مرحله بعد',
      rollback: 'gcloud auth login',
      notes: ['مطمئن شوید در پروژه درست هستید']
    });
  }
  
  return commands;
}

/**
 * ✅ v17.0: تولید دستورات خاص هر مرحله
 */
function generatePhaseSpecificCommands(projectType, phaseName, context) {
  const commands = [];
  
  // === دستورات برای پروژه‌های Google Apps Script ===
  if (projectType === 'coding' && context.platform?.id === 'google_apps_script') {
    
    if (phaseName.includes('تحلیل') || phaseName.includes('نیازمندی')) {
      commands.push({
        phase: phaseName,
        task: 'استخراج کد موجود از Apps Script',
        command: 'clasp pull',
        params: [],
        expectedOutput: 'فایل‌های .gs و .html دانلود می‌شوند',
        validation: 'بررسی کنید فایل‌ها در پوشه دانلود شده‌اند',
        nextStep: 'تحلیل فایل‌های دانلود شده',
        rollback: 'clasp login',
        notes: ['اگر clasp نصب نیست: npm install -g @google/clasp']
      });
    }
    
    if (phaseName.includes('پیاده‌سازی') || phaseName.includes('کدنویسی')) {
      commands.push({
        phase: phaseName,
        task: 'آپلود تغییرات به Apps Script',
        command: 'clasp push',
        params: [],
        expectedOutput: 'Pushed N files successfully',
        validation: 'اگر "Pushed X files" نمایش داده شد، آپلود موفق بوده',
        nextStep: 'تست در محیط Apps Script',
        rollback: 'clasp pull',
        notes: ['قبل از push، کد را ذخیره کنید']
      });
      
      commands.push({
        phase: phaseName,
        task: 'باز کردن ادیتور Apps Script',
        command: 'clasp open',
        params: [],
        expectedOutput: 'مرورگر باز می‌شود با ادیتور',
        validation: 'ادیتور باید در مرورگر باز شود',
        nextStep: 'اجرای تست در ادیتور',
        rollback: '',
        notes: []
      });
    }
    
    if (phaseName.includes('استقرار') || phaseName.includes('دیپلوی')) {
      commands.push({
        phase: phaseName,
        task: 'ایجاد نسخه جدید',
        command: 'clasp version "نسخه جدید"',
        params: ['description: توضیحات نسخه'],
        expectedOutput: 'Created version X',
        validation: 'شماره نسخه باید نمایش داده شود',
        nextStep: 'دیپلوی نسخه جدید',
        rollback: '',
        notes: []
      });
      
      commands.push({
        phase: phaseName,
        task: 'دیپلوی به عنوان Web App',
        command: 'clasp deploy --versionNumber X',
        params: ['versionNumber: شماره نسخه'],
        expectedOutput: 'Deployed script with ID: ...',
        validation: 'Deployment ID باید نمایش داده شود',
        nextStep: 'تست Web App',
        rollback: 'clasp undeploy --deploymentId [ID]',
        notes: ['شماره نسخه از مرحله قبل را وارد کنید']
      });
    }
  }
  
  // === دستورات برای پروژه‌های Google Cloud ===
  if (context.platform?.id === 'google_console') {
    
    if (phaseName.includes('استقرار')) {
      commands.push({
        phase: phaseName,
        task: 'دیپلوی به App Engine',
        command: 'gcloud app deploy',
        params: ['--project=[PROJECT_ID]', '--version=[VERSION]'],
        expectedOutput: 'Deployed service [default] to [URL]',
        validation: 'URL باید نمایش داده شود',
        nextStep: 'تست URL',
        rollback: 'gcloud app versions stop [VERSION]',
        notes: ['مطمئن شوید app.yaml وجود دارد']
      });
      
      commands.push({
        phase: phaseName,
        task: 'مشاهده لاگ‌ها',
        command: 'gcloud app logs tail -s default',
        params: [],
        expectedOutput: 'نمایش لاگ‌های زنده',
        validation: 'لاگ‌ها باید جریان یابند',
        nextStep: 'بررسی خطاها در لاگ',
        rollback: '',
        notes: ['با Ctrl+C متوقف کنید']
      });
    }
  }
  
  // === دستورات عمومی برای همه پروژه‌ها ===
  if (phaseName.includes('تست')) {
    commands.push({
      phase: phaseName,
      task: 'اجرای تست‌ها',
      command: 'npm test',
      params: [],
      expectedOutput: 'All tests passed',
      validation: 'نباید خطای FAIL وجود داشته باشد',
      nextStep: 'رفع خطاهای تست در صورت وجود',
      rollback: '',
      notes: ['اگر Jest استفاده می‌شود: npm run test:coverage']
    });
  }
  
  return commands;
}

/**
 * ✅ v17.0: فرمت‌بندی دستورات برای نمایش
 */
function formatCommandsForDisplay(commands) {
  let output = `# 📋 دستورات اجرایی\n\n`;
  output += `**محیط اجرا:** ${commands.environment.icon} ${commands.environment.label}\n`;
  output += `**فاز جاری:** ${commands.currentPhase}\n`;
  output += `**تاریخ:** ${new Date(commands.timestamp).toLocaleDateString('fa-IR')}\n\n`;
  output += `---\n\n`;
  
  for (const step of commands.steps) {
    output += `## مرحله ${step.step}: ${step.task}\n\n`;
    output += `**فاز:** ${step.phase}\n\n`;
    output += `**دستور:**\n\`\`\`bash\n${step.command}\n\`\`\`\n\n`;
    
    if (step.params && step.params.length > 0) {
      output += `**پارامترها:**\n`;
      for (const param of step.params) {
        output += `- \`${param}\`\n`;
      }
      output += '\n';
    }
    
    output += `**خروجی مورد انتظار:**\n> ${step.expectedOutput}\n\n`;
    output += `**اعتبارسنجی:**\n> ${step.validation}\n\n`;
    
    if (step.nextStep) {
      output += `**گام بعدی:** ${step.nextStep}\n\n`;
    }
    
    if (step.rollback) {
      output += `**در صورت خطا:**\n\`\`\`bash\n${step.rollback}\n\`\`\`\n\n`;
    }
    
    if (step.notes && step.notes.length > 0) {
      output += `**توجه:**\n`;
      for (const note of step.notes) {
        output += `- ⚠️ ${note}\n`;
      }
      output += '\n';
    }
    
    output += `---\n\n`;
  }
  
  return output;
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 4: COMMAND FEEDBACK SYSTEM
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0: پردازش بازخورد اجرای دستور
 * @param {string} projectId - شناسه پروژه
 * @param {number} stepNumber - شماره مرحله
 * @param {Object} feedback - بازخورد کاربر
 * @returns {Object} - نتیجه پردازش
 */
function processCommandFeedback(projectId, stepNumber, feedback) {
  try {
    Logger.log(`📝 پردازش بازخورد برای پروژه ${projectId}, مرحله ${stepNumber}`);
    
    const result = {
      success: true,
      analysis: {},
      nextActions: []
    };
    
    // تحلیل خروجی
    const outputAnalysis = analyzeCommandOutput(feedback.output, feedback.expectedOutput);
    result.analysis = outputAnalysis;
    
    // تعیین اقدامات بعدی
    if (outputAnalysis.status === 'success') {
      result.nextActions.push({
        type: 'proceed',
        message: 'خروجی مطابق انتظار است. به مرحله بعد بروید.',
        confidence: outputAnalysis.confidence
      });
      
      // به‌روزرسانی پیشرفت پروژه
      updateProjectProgress(projectId, stepNumber, 'completed');
      
    } else if (outputAnalysis.status === 'partial') {
      result.nextActions.push({
        type: 'review',
        message: 'خروجی تا حدی مطابق انتظار است. بررسی بیشتر لازم است.',
        details: outputAnalysis.issues
      });
      
    } else {
      result.nextActions.push({
        type: 'troubleshoot',
        message: 'خروجی مطابق انتظار نیست.',
        suggestions: generateTroubleshootingSuggestions(feedback.output, feedback.command)
      });
      
      // ثبت خطا
      logCommandError(projectId, stepNumber, feedback);
    }
    
    return result;
    
  } catch (error) {
    Logger.log('❌ خطا در پردازش بازخورد: ' + error);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * ✅ v17.0: تحلیل خروجی دستور
 */
function analyzeCommandOutput(actualOutput, expectedOutput) {
  const analysis = {
    status: 'unknown',
    confidence: 0,
    issues: [],
    matches: []
  };
  
  if (!actualOutput) {
    analysis.status = 'error';
    analysis.issues.push('خروجی خالی است');
    return analysis;
  }
  
  const actual = actualOutput.toLowerCase();
  const expected = (expectedOutput || '').toLowerCase();
  
  // بررسی الگوهای موفقیت
  const successPatterns = [
    'success', 'successfully', 'done', 'complete', 'passed',
    'موفق', 'انجام شد', 'تکمیل'
  ];
  
  // بررسی الگوهای خطا
  const errorPatterns = [
    'error', 'failed', 'failure', 'exception', 'denied', 'not found',
    'خطا', 'ناموفق', 'شکست'
  ];
  
  // شمارش تطابق‌ها
  let successCount = 0;
  let errorCount = 0;
  
  for (const pattern of successPatterns) {
    if (actual.includes(pattern)) {
      successCount++;
      analysis.matches.push(pattern);
    }
  }
  
  for (const pattern of errorPatterns) {
    if (actual.includes(pattern)) {
      errorCount++;
      analysis.issues.push(`الگوی خطا یافت شد: ${pattern}`);
    }
  }
  
  // تعیین وضعیت
  if (errorCount > 0 && successCount === 0) {
    analysis.status = 'error';
    analysis.confidence = 90;
  } else if (successCount > 0 && errorCount === 0) {
    analysis.status = 'success';
    analysis.confidence = 85;
  } else if (successCount > 0 && errorCount > 0) {
    analysis.status = 'partial';
    analysis.confidence = 60;
  } else {
    // بررسی تطابق با خروجی مورد انتظار
    if (expected && actual.includes(expected.substring(0, 20))) {
      analysis.status = 'success';
      analysis.confidence = 70;
    } else {
      analysis.status = 'unknown';
      analysis.confidence = 30;
      analysis.issues.push('نمی‌توان وضعیت را تشخیص داد');
    }
  }
  
  return analysis;
}

/**
 * ✅ v17.0: تولید پیشنهادات رفع مشکل
 */
function generateTroubleshootingSuggestions(output, command) {
  const suggestions = [];
  const outputLower = (output || '').toLowerCase();
  
  // تشخیص مشکلات رایج
  if (outputLower.includes('permission denied') || outputLower.includes('access denied')) {
    suggestions.push({
      issue: 'مشکل دسترسی',
      solution: 'دستور را با sudo اجرا کنید یا دسترسی‌ها را بررسی کنید'
    });
  }
  
  if (outputLower.includes('not found') || outputLower.includes('command not found')) {
    suggestions.push({
      issue: 'دستور یافت نشد',
      solution: 'ابزار مربوطه را نصب کنید یا مسیر را بررسی کنید'
    });
  }
  
  if (outputLower.includes('connection') || outputLower.includes('timeout')) {
    suggestions.push({
      issue: 'مشکل اتصال',
      solution: 'اتصال اینترنت و فایروال را بررسی کنید'
    });
  }
  
  if (outputLower.includes('auth') || outputLower.includes('login') || outputLower.includes('credential')) {
    suggestions.push({
      issue: 'مشکل احراز هویت',
      solution: 'مجدداً وارد شوید: gcloud auth login یا clasp login'
    });
  }
  
  if (outputLower.includes('quota') || outputLower.includes('limit')) {
    suggestions.push({
      issue: 'محدودیت quota',
      solution: 'چند دقیقه صبر کنید یا quota را در کنسول افزایش دهید'
    });
  }
  
  // پیشنهاد عمومی
  if (suggestions.length === 0) {
    suggestions.push({
      issue: 'خطای نامشخص',
      solution: 'خروجی کامل را کپی کرده و برای تحلیل ارسال کنید'
    });
  }
  
  return suggestions;
}

/**
 * ✅ v17.0: به‌روزرسانی پیشرفت پروژه
 */
function updateProjectProgress(projectId, stepNumber, status) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context) return;
    
    // ثبت تکمیل مرحله
    if (!context.commandHistory) {
      context.commandHistory = [];
    }
    
    context.commandHistory.push({
      step: stepNumber,
      status: status,
      timestamp: new Date().toISOString()
    });
    
    saveSmartProjectContext(projectId, context);
    
  } catch (e) {
    Logger.log('⚠️ خطا در به‌روزرسانی پیشرفت: ' + e);
  }
}

/**
 * ✅ v17.0: ثبت خطای دستور
 */
function logCommandError(projectId, stepNumber, feedback) {
  try {
    logToJournal('command_error', 'project', {
      projectId: projectId,
      step: stepNumber,
      command: feedback.command,
      output: (feedback.output || '').substring(0, 500),
      timestamp: new Date().toISOString()
    });
  } catch (e) {
    Logger.log('⚠️ خطا در ثبت لاگ: ' + e);
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 5: API ENDPOINTS FOR PHASE 1
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0: API - تحلیل پروژه خارجی
 */
function apiAnalyzeExternalProject(files, metadata) {
  return analyzeExternalProject(files, metadata || {});
}

/**
 * ✅ v17.0: API - تولید دستورات اجرایی
 */
function apiGenerateCommands(projectId) {
  const context = loadSmartProjectContext(projectId);
  if (!context) {
    return { success: false, error: 'پروژه یافت نشد' };
  }
  return generateExecutableCommands(projectId, context);
}

/**
 * ✅ v17.0: API - پردازش بازخورد دستور
 */
function apiProcessCommandFeedback(projectId, stepNumber, feedback) {
  return processCommandFeedback(projectId, stepNumber, feedback);
}

/**
 * ✅ v17.0: API - دریافت نمودار Mermaid
 */
function apiGetMermaidDiagram(projectId, diagramType) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    // اگر تحلیل قبلی موجود است
    if (context.analysis && context.analysis.diagrams) {
      const diagrams = context.analysis.diagrams;
      
      switch (diagramType) {
        case 'architecture':
          return { success: true, diagram: diagrams.architecture };
        case 'dataflow':
          return { success: true, diagram: diagrams.dataFlow };
        case 'component':
          return { success: true, diagram: diagrams.componentTree };
        default:
          return { 
            success: true, 
            diagrams: diagrams 
          };
      }
    }
    
    return { success: false, error: 'نمودار یافت نشد. ابتدا پروژه را تحلیل کنید.' };
    
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * ✅ v17.0: API - تحلیل سریع با تولید نمودار
 */
function apiQuickAnalyzeWithDiagram(files) {
  const analysis = analyzeExternalProject(files, {});
  
  if (analysis.success) {
    return {
      success: true,
      summary: analysis.analysis.summary,
      diagrams: analysis.analysis.diagrams,
      roadmap: analysis.analysis.roadmap,
      issues: analysis.analysis.issues
    };
  }
  
  return analysis;
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 END OF PHASE 1 - SMART ENGINEERING THINK TANK
// ═══════════════════════════════════════════════════════════════════════════════
// ═══════════════════════════════════════════════════════════════════════════════
// ╔═══════════════════════════════════════════════════════════════════════════════╗
// ║  🗺️ اتاق فکر مهندسی هوشمند - فاز ۲                                            ║
// ║  نسخه: 17.0 - DYNAMIC ROADMAP SYSTEM                                          ║
// ╠═══════════════════════════════════════════════════════════════════════════════╣
// ║  ✅ نقشه راه داینامیک با وابستگی تسک‌ها                                       ║
// ║  ✅ Milestones و KPIs قابل اندازه‌گیری                                        ║
// ║  ✅ نمودار Gantt و Critical Path                                              ║
// ║  ✅ به‌روزرسانی خودکار بر اساس پیشرفت                                         ║
// ║  ✅ تشخیص انحراف و هشدار                                                       ║
// ║  ✅ پایش Real-time                                                             ║
// ╚═══════════════════════════════════════════════════════════════════════════════╝

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 0: SMART PROJECT CONTEXT HELPERS (Phase 2/3)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0: بارگذاری context پروژه - wrapper برای Phase 2/3
 */
function loadSmartProjectContext(projectId) {
  try {
    if (!projectId) return null;
    
    const result = loadPersistentProject(projectId);
    if (!result.success) {
      Logger.log('⚠️ پروژه یافت نشد: ' + projectId);
      return null;
    }
    
    // اطمینان از وجود roadmap در context
    if (!result.context.roadmap) {
      result.context.roadmap = {
        tasks: [],
        milestones: [],
        lastUpdated: null
      };
    }
    
    // اطمینان از وجود evaluationHistory
    if (!result.context.evaluationHistory) {
      result.context.evaluationHistory = [];
    }
    
    return result.context;
    
  } catch (error) {
    Logger.log('❌ خطا در loadSmartProjectContext: ' + error);
    return null;
  }
}

/**
 * ✅ v17.0: ذخیره context پروژه - wrapper برای Phase 2/3
 */
function saveSmartProjectContext(projectId, context) {
  try {
    if (!projectId || !context) return false;
    
    const registry = getPersistentProjectRegistry();
    const projectInfo = registry[projectId];
    
    if (!projectInfo) {
      Logger.log('⚠️ پروژه یافت نشد برای ذخیره: ' + projectId);
      return false;
    }
    
    // به‌روزرسانی timestamp
    context.lastUpdated = new Date().toISOString();
    if (context.roadmap) {
      context.roadmap.lastUpdated = context.lastUpdated;
    }
    
    // ذخیره در فایل context
    const contextFile = DriveApp.getFileById(projectInfo.contextFileId);
    contextFile.setContent(JSON.stringify(context, null, 2));
    
    // ✅ v17.1.2: همگام‌سازی با spreadsheet و flowchart
    syncContextToSpreadsheet(projectId, projectInfo, context);
    
    Logger.log('✅ context ذخیره شد: ' + projectId);
    return true;
    
  } catch (error) {
    Logger.log('❌ خطا در saveSmartProjectContext: ' + error);
    return false;
  }
}

/**
 * ✅ v17.1.2: همگام‌سازی context با فایل‌های Google Drive
 */
function syncContextToSpreadsheet(projectId, projectInfo, context) {
  try {
    if (!projectInfo || !projectInfo.folderId) return;
    
    const folder = DriveApp.getFolderById(projectInfo.folderId);
    
    // 1. به‌روزرسانی Dashboard
    syncDashboardSheet(folder, context, projectInfo);
    
    // 2. به‌روزرسانی Phases
    syncPhasesSheet(folder, context);
    
    // 3. به‌روزرسانی Tasks (نقشه راه)
    syncTasksSheet(folder, context);
    
    // 4. به‌روزرسانی Timeline
    syncTimelineSheet(folder, context);
    
    // ✅ v17.1.4: به‌روزرسانی Conversations
    syncConversationsSheet(folder, context);
    
    // ✅ v17.1.5: به‌روزرسانی Files Registry
    syncFilesRegistrySheet(folder, context);
    
    // ✅ v17.1.5: به‌روزرسانی Models Performance
    syncModelsPerformanceSheet(folder, context);
    
    // 5. به‌روزرسانی Flowchart
    updatePersistentFlowchart(projectInfo, context);
    
    Logger.log('✅ همگام‌سازی با spreadsheet انجام شد');
    
  } catch (error) {
    Logger.log('⚠️ خطا در همگام‌سازی: ' + error);
  }
}

/**
 * ✅ v17.1.5: به‌روزرسانی شیت Files Registry
 */
function syncFilesRegistrySheet(folder, context) {
  try {
    const files = folder.getFilesByName('Project_Master');
    if (!files.hasNext()) return;
    
    const ss = SpreadsheetApp.open(files.next());
    let sheet = ss.getSheetByName('Files Registry');
    
    if (!sheet) {
      sheet = ss.insertSheet('Files Registry');
    }
    
    sheet.clear();
    
    // هدر
    const headers = ['#', 'نام فایل', 'نوع', 'دسته‌بندی', 'اندازه', 'تاریخ ایجاد', 'توضیحات'];
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold').setBackground('#1a73e8').setFontColor('white');
    
    // داده‌های فایل‌ها
    const filesList = context.files || [];
    if (filesList.length > 0) {
      const data = filesList.map((file, index) => [
        index + 1,
        file.name || '-',
        file.type || file.mimeType || '-',
        file.category || '-',
        file.size ? formatFileSize(file.size) : '-',
        file.createdAt ? new Date(file.createdAt).toLocaleString('fa-IR') : '-',
        file.description || '-'
      ]);
      
      sheet.getRange(2, 1, data.length, headers.length).setValues(data);
    }
    
    // تنظیم عرض ستون‌ها
    sheet.setColumnWidth(2, 250); // نام فایل
    sheet.setColumnWidth(7, 300); // توضیحات
    
  } catch (error) {
    Logger.log('⚠️ خطا در syncFilesRegistrySheet: ' + error);
  }
}

/**
 * ✅ v17.1.5: به‌روزرسانی شیت Models Performance
 */
function syncModelsPerformanceSheet(folder, context) {
  try {
    const files = folder.getFilesByName('Project_Master');
    if (!files.hasNext()) return;
    
    const ss = SpreadsheetApp.open(files.next());
    let sheet = ss.getSheetByName('Models Performance');
    
    if (!sheet) {
      sheet = ss.insertSheet('Models Performance');
    }
    
    sheet.clear();
    
    // هدر
    const headers = ['#', 'نام مدل', 'Provider', 'تعداد استفاده', 'امتیاز میانگین', 'آخرین استفاده', 'وضعیت'];
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold').setBackground('#1a73e8').setFontColor('white');
    
    // داده‌های مدل‌ها
    const models = context.models || { active: [], scores: {} };
    const activeModels = models.active || [];
    const scores = models.scores || {};
    
    if (activeModels.length > 0) {
      const data = activeModels.map((modelId, index) => {
        const score = scores[modelId] || { count: 0, average: 0 };
        const provider = detectModelProvider(modelId);
        
        return [
          index + 1,
          modelId,
          provider,
          score.count || 0,
          (score.average || 0).toFixed(1),
          score.lastUsed ? new Date(score.lastUsed).toLocaleString('fa-IR') : '-',
          models.primary === modelId ? '⭐ اصلی' : '✓ فعال'
        ];
      });
      
      sheet.getRange(2, 1, data.length, headers.length).setValues(data);
      
      // رنگ‌بندی
      for (let i = 0; i < activeModels.length; i++) {
        const rowIndex = i + 2;
        if (models.primary === activeModels[i]) {
          sheet.getRange(rowIndex, 1, 1, headers.length).setBackground('#e8f5e9');
        }
      }
    }
    
    // تنظیم عرض ستون‌ها
    sheet.setColumnWidth(2, 200); // نام مدل
    
  } catch (error) {
    Logger.log('⚠️ خطا در syncModelsPerformanceSheet: ' + error);
  }
}

/**
 * ✅ v17.1.5: دریافت نام نمایشی مدل
 * @param {string} modelId - شناسه مدل
 * @returns {string} نام نمایشی مدل
 */
function getModelDisplayName(modelId) {
  if (!modelId) return 'AI';
  
  // بررسی در MODEL_REGISTRY
  if (typeof MODEL_REGISTRY !== 'undefined' && MODEL_REGISTRY[modelId]) {
    return MODEL_REGISTRY[modelId].name || modelId;
  }
  
  // نام‌های شناخته شده
  const knownNames = {
    'gpt-4-turbo': 'GPT-4 Turbo',
    'gpt-4': 'GPT-4',
    'gpt-4o': 'GPT-4o',
    'gpt-4o-mini': 'GPT-4o Mini',
    'gpt-3.5-turbo': 'GPT-3.5 Turbo',
    'claude-sonnet-4-20250514': 'Claude Sonnet 4',
    'claude-3-5-sonnet-20241022': 'Claude 3.5 Sonnet',
    'claude-3-opus-20240229': 'Claude 3 Opus',
    'claude-3-haiku-20240307': 'Claude 3 Haiku',
    'gemini-2.5-pro': 'Gemini 1.5 Pro',
    'gemini-2.5-flash': 'Gemini 1.5 Flash',
    'gemini-2.0-flash': 'Gemini 2.0 Flash',
    'deepseek-chat': 'DeepSeek Chat',
    'deepseek-coder': 'DeepSeek Coder'
  };
  
  if (knownNames[modelId]) {
    return knownNames[modelId];
  }
  
  // سعی در تولید نام خوانا
  return modelId
    .replace(/-/g, ' ')
    .replace(/(\d)/g, ' $1')
    .replace(/\s+/g, ' ')
    .trim()
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// ✅ v17.1.5: تشخیص provider از نام مدل
function detectModelProvider(modelId) {
  if (!modelId) return 'Unknown';
  const id = modelId.toLowerCase();
  if (id.includes('gpt') || id.includes('openai') || id.includes('o1')) return 'OpenAI';
  if (id.includes('claude') || id.includes('anthropic')) return 'Anthropic';
  if (id.includes('gemini') || id.includes('google')) return 'Google';
  if (id.includes('deepseek')) return 'DeepSeek';
  if (id.includes('mistral')) return 'Mistral';
  if (id.includes('llama') || id.includes('meta')) return 'Meta';
  if (id.includes('qwen')) return 'Alibaba';
  return 'Other';
}

// ✅ v17.1.5: فرمت‌بندی اندازه فایل
function formatFileSize(bytes) {
  if (!bytes) return '-';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  while (bytes >= 1024 && i < units.length - 1) {
    bytes /= 1024;
    i++;
  }
  return bytes.toFixed(1) + ' ' + units[i];
}

/**
 * ✅ v17.1.4: به‌روزرسانی شیت Conversations
 */
function syncConversationsSheet(folder, context) {
  try {
    const files = folder.getFilesByName('Project_Master');
    if (!files.hasNext()) return;
    
    const ss = SpreadsheetApp.open(files.next());
    let sheet = ss.getSheetByName('Conversations');
    
    if (!sheet) {
      sheet = ss.insertSheet('Conversations');
    }
    
    sheet.clear();
    
    // هدر
    const headers = ['#', 'زمان', 'فاز', 'ورودی کاربر', 'مدل', 'پاسخ', 'امتیاز', 'مدت (ثانیه)'];
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold').setBackground('#1a73e8').setFontColor('white');
    
    // داده‌های مکالمات
    const conversations = context.conversations || [];
    if (conversations.length > 0) {
      const data = conversations.map((conv, index) => [
        index + 1,
        conv.timestamp ? new Date(conv.timestamp).toLocaleString('fa-IR') : '-',
        conv.phase || '-',
        String(conv.userMessage || conv.message || '').substring(0, 300),
        conv.model || 'AI',
        String(conv.aiResponse || conv.response || '').substring(0, 500),
        conv.score || '-',
        conv.duration || '-'
      ]);
      
      sheet.getRange(2, 1, data.length, headers.length).setValues(data);
      
      // رنگ‌بندی ردیف‌ها
      for (let i = 0; i < conversations.length; i++) {
        const rowIndex = i + 2;
        const bgColor = i % 2 === 0 ? '#ffffff' : '#f8f9fa';
        sheet.getRange(rowIndex, 1, 1, headers.length).setBackground(bgColor);
      }
    }
    
    // تنظیم عرض ستون‌ها
    sheet.setColumnWidth(4, 300); // ورودی کاربر
    sheet.setColumnWidth(6, 400); // پاسخ
    
  } catch (error) {
    Logger.log('⚠️ خطا در syncConversationsSheet: ' + error);
  }
}

/**
 * ✅ v17.1.2: به‌روزرسانی شیت Dashboard
 */
function syncDashboardSheet(folder, context, projectInfo) {
  try {
    const files = folder.getFilesByName('Project_Master');
    if (!files.hasNext()) return;
    
    const ss = SpreadsheetApp.open(files.next());
    let sheet = ss.getSheetByName('Dashboard');
    
    if (!sheet) {
      sheet = ss.insertSheet('Dashboard');
    }
    
    // پاک کردن و بازنویسی
    sheet.clear();
    
    // محاسبه آمار
    const phases = context.phases || [];
    const tasks = context.roadmap?.tasks || [];
    const completedPhases = phases.filter(p => p.status === 'completed').length;
    const completedTasks = tasks.filter(t => t.status === 'completed').length;
    const inProgressTasks = tasks.filter(t => t.status === 'in_progress').length;
    const pendingTasks = tasks.filter(t => t.status === 'not_started' || t.status === 'pending').length;
    const blockedTasks = tasks.filter(t => t.status === 'blocked').length;
    
    // هدر
    sheet.getRange('A1:D1').setValues([['📊 داشبورد پروژه', '', '', '']]);
    sheet.getRange('A1:D1').merge().setFontSize(16).setFontWeight('bold').setBackground('#4285f4').setFontColor('white');
    
    // اطلاعات کلی
    const dashboardData = [
      ['', '', '', ''],
      ['🏷️ نام پروژه', context.project?.name || projectInfo?.name || '-', '', ''],
      ['📅 تاریخ ایجاد', context.createdAt ? new Date(context.createdAt).toLocaleString('fa-IR') : '-', '', ''],
      ['🔄 آخرین به‌روزرسانی', new Date().toLocaleString('fa-IR'), '', ''],
      ['', '', '', ''],
      ['📈 آمار کلی', '', '', ''],
      ['فازها', `${completedPhases} از ${phases.length} تکمیل`, '', ''],
      ['تسک‌ها', `${completedTasks} از ${tasks.length} تکمیل`, '', ''],
      ['', '', '', ''],
      ['📋 وضعیت تسک‌ها', 'تعداد', '', ''],
      ['✅ تکمیل شده', completedTasks, '', ''],
      ['🔄 در حال انجام', inProgressTasks, '', ''],
      ['⏳ در انتظار', pendingTasks, '', ''],
      ['🚫 مسدود', blockedTasks, '', ''],
      ['', '', '', ''],
      ['📊 پیشرفت کلی', calculateOverallProgressSafe(phases, tasks) + '%', '', '']
    ];
    
    sheet.getRange(2, 1, dashboardData.length, 4).setValues(dashboardData);
    
    // فرمت‌بندی
    sheet.setColumnWidth(1, 200);
    sheet.setColumnWidth(2, 200);
    sheet.getRange('A6').setFontWeight('bold').setBackground('#e8f0fe');
    sheet.getRange('A10').setFontWeight('bold').setBackground('#e8f0fe');
    sheet.getRange('A16').setFontWeight('bold').setBackground('#fce8e6');
    
  } catch (error) {
    Logger.log('⚠️ خطا در syncDashboardSheet: ' + error);
  }
}

/**
 * ✅ v17.1.2: به‌روزرسانی شیت Phases
 */
function syncPhasesSheet(folder, context) {
  try {
    const files = folder.getFilesByName('Project_Master');
    if (!files.hasNext()) return;
    
    const ss = SpreadsheetApp.open(files.next());
    let sheet = ss.getSheetByName('Phases');
    
    if (!sheet) {
      sheet = ss.insertSheet('Phases');
    }
    
    sheet.clear();
    
    // هدر
    const headers = ['#', 'نام فاز', 'وضعیت', 'پیشرفت', 'تاریخ شروع', 'تاریخ پایان', 'یادداشت'];
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold').setBackground('#4285f4').setFontColor('white');
    
    // داده‌های فازها
    const phases = context.phases || [];
    if (phases.length > 0) {
      const data = phases.map((phase, index) => [
        index + 1,
        phase.name || '-',
        getStatusLabel(phase.status),
        (phase.progress || 0) + '%',
        phase.startedAt ? new Date(phase.startedAt).toLocaleDateString('fa-IR') : '-',
        phase.completedAt ? new Date(phase.completedAt).toLocaleDateString('fa-IR') : '-',
        (phase.notes && phase.notes.length > 0) ? phase.notes[phase.notes.length - 1].text || '' : ''
      ]);
      
      sheet.getRange(2, 1, data.length, headers.length).setValues(data);
      
      // رنگ‌بندی بر اساس وضعیت
      for (let i = 0; i < phases.length; i++) {
        const rowIndex = i + 2;
        const status = phases[i].status;
        let bgColor = '#ffffff';
        
        if (status === 'completed') bgColor = '#d5f5e3';
        else if (status === 'in_progress') bgColor = '#d4e6f1';
        else if (status === 'failed') bgColor = '#fadbd8';
        
        sheet.getRange(rowIndex, 1, 1, headers.length).setBackground(bgColor);
      }
    }
    
  } catch (error) {
    Logger.log('⚠️ خطا در syncPhasesSheet: ' + error);
  }
}

/**
 * ✅ v17.1.2: به‌روزرسانی شیت Tasks
 */
function syncTasksSheet(folder, context) {
  try {
    const files = folder.getFilesByName('Project_Master');
    if (!files.hasNext()) return;
    
    const ss = SpreadsheetApp.open(files.next());
    let sheet = ss.getSheetByName('Tasks');
    
    if (!sheet) {
      sheet = ss.insertSheet('Tasks');
    }
    
    sheet.clear();
    
    // هدر
    const headers = ['#', 'نام تسک', 'وضعیت', 'اولویت', 'پیشرفت', 'مدت (روز)', 'شروع', 'پایان', 'وابستگی‌ها', 'ایجاد خودکار'];
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold').setBackground('#34a853').setFontColor('white');
    
    // داده‌های تسک‌ها
    const tasks = context.roadmap?.tasks || [];
    if (tasks.length > 0) {
      const data = tasks.map((task, index) => [
        index + 1,
        task.name || '-',
        getTaskStatusLabel(task.status),
        getPriorityLabel(task.priority),
        (task.progress || 0) + '%',
        task.estimatedDays || 1,
        task.plannedStartDate ? new Date(task.plannedStartDate).toLocaleDateString('fa-IR') : '-',
        task.plannedEndDate ? new Date(task.plannedEndDate).toLocaleDateString('fa-IR') : '-',
        (task.dependencies || []).join(', ') || '-',
        task.autoCreated ? '✅' : ''
      ]);
      
      sheet.getRange(2, 1, data.length, headers.length).setValues(data);
      
      // رنگ‌بندی
      for (let i = 0; i < tasks.length; i++) {
        const rowIndex = i + 2;
        const status = tasks[i].status;
        let bgColor = '#ffffff';
        
        if (status === 'completed') bgColor = '#d5f5e3';
        else if (status === 'in_progress') bgColor = '#d4e6f1';
        else if (status === 'blocked') bgColor = '#fadbd8';
        
        sheet.getRange(rowIndex, 1, 1, headers.length).setBackground(bgColor);
        
        // رنگ اولویت
        const priority = tasks[i].priority;
        let priorityColor = '#000000';
        if (priority === 'critical' || priority === 'high') priorityColor = '#e74c3c';
        else if (priority === 'low') priorityColor = '#27ae60';
        
        sheet.getRange(rowIndex, 4).setFontColor(priorityColor).setFontWeight('bold');
      }
    }
    
    // تنظیم عرض ستون‌ها
    sheet.setColumnWidth(2, 300);
    
  } catch (error) {
    Logger.log('⚠️ خطا در syncTasksSheet: ' + error);
  }
}

/**
 * ✅ v17.1.2: به‌روزرسانی شیت Timeline
 */
function syncTimelineSheet(folder, context) {
  try {
    const files = folder.getFilesByName('Project_Master');
    if (!files.hasNext()) return;
    
    const ss = SpreadsheetApp.open(files.next());
    let sheet = ss.getSheetByName('Timeline');
    
    if (!sheet) {
      sheet = ss.insertSheet('Timeline');
    }
    
    sheet.clear();
    
    // هدر
    sheet.getRange('A1:E1').setValues([['📅 خط زمانی پروژه', '', '', '', '']]);
    sheet.getRange('A1:E1').merge().setFontSize(14).setFontWeight('bold').setBackground('#fbbc04').setFontColor('white');
    
    // ترکیب فازها و تسک‌ها
    const timeline = [];
    
    // اضافه کردن فازها
    const phases = context.phases || [];
    phases.forEach((phase, index) => {
      timeline.push({
        date: phase.startedAt || phase.createdAt || context.createdAt,
        type: 'فاز',
        name: phase.name,
        status: phase.status,
        details: `فاز ${index + 1}`
      });
    });
    
    // اضافه کردن تسک‌ها
    const tasks = context.roadmap?.tasks || [];
    tasks.forEach(task => {
      timeline.push({
        date: task.createdAt,
        type: 'تسک',
        name: task.name,
        status: task.status,
        details: task.autoCreated ? 'ایجاد خودکار' : 'دستی'
      });
    });
    
    // مرتب‌سازی بر اساس تاریخ
    timeline.sort((a, b) => new Date(a.date || 0) - new Date(b.date || 0));
    
    // هدر جدول
    const headers = ['تاریخ', 'نوع', 'نام', 'وضعیت', 'جزئیات'];
    sheet.getRange(3, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(3, 1, 1, headers.length).setFontWeight('bold').setBackground('#e8eaed');
    
    // داده‌ها
    if (timeline.length > 0) {
      const data = timeline.map(item => [
        item.date ? new Date(item.date).toLocaleString('fa-IR') : '-',
        item.type,
        item.name,
        getStatusLabel(item.status),
        item.details
      ]);
      
      sheet.getRange(4, 1, data.length, headers.length).setValues(data);
    }
    
  } catch (error) {
    Logger.log('⚠️ خطا در syncTimelineSheet: ' + error);
  }
}

// توابع کمکی
function getStatusLabel(status) {
  const labels = {
    'pending': '⏳ در انتظار',
    'in_progress': '🔄 در حال انجام',
    'completed': '✅ تکمیل شده',
    'failed': '❌ ناموفق',
    'paused': '⏸️ متوقف',
    'not_started': '⏳ شروع نشده',
    'blocked': '🚫 مسدود'
  };
  return labels[status] || status || '-';
}

function getTaskStatusLabel(status) {
  return getStatusLabel(status);
}

function getPriorityLabel(priority) {
  const labels = {
    'critical': '🔴 بحرانی',
    'high': '🟠 بالا',
    'medium': '🟡 متوسط',
    'low': '🟢 پایین'
  };
  return labels[priority] || priority || '🟡 متوسط';
}

function calculateOverallProgressSafe(phases, tasks) {
  try {
    let total = 0;
    let count = 0;
    
    if (phases && phases.length > 0) {
      phases.forEach(p => {
        total += (p.progress || 0);
        count++;
      });
    }
    
    if (tasks && tasks.length > 0) {
      const completedTasks = tasks.filter(t => t.status === 'completed').length;
      total += Math.round((completedTasks / tasks.length) * 100);
      count++;
    }
    
    return count > 0 ? Math.round(total / count) : 0;
  } catch (e) {
    return 0;
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 1: DYNAMIC ROADMAP CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0 Phase 2: تنظیمات سیستم نقشه راه داینامیک
 */
const DYNAMIC_ROADMAP_CONFIG = {
  // وضعیت‌های تسک
  TASK_STATUS: {
    NOT_STARTED: { id: 'not_started', label: 'شروع نشده', color: '#9ca3af', icon: '⏳' },
    IN_PROGRESS: { id: 'in_progress', label: 'در حال انجام', color: '#3b82f6', icon: '🔄' },
    BLOCKED: { id: 'blocked', label: 'مسدود شده', color: '#ef4444', icon: '🚫' },
    COMPLETED: { id: 'completed', label: 'تکمیل شده', color: '#10b981', icon: '✅' },
    SKIPPED: { id: 'skipped', label: 'رد شده', color: '#6b7280', icon: '⏭️' },
    DELAYED: { id: 'delayed', label: 'تأخیر دارد', color: '#f59e0b', icon: '⚠️' }
  },
  
  // اولویت‌های تسک
  PRIORITY: {
    CRITICAL: { id: 'critical', label: 'بحرانی', weight: 4, color: '#dc2626' },
    HIGH: { id: 'high', label: 'بالا', weight: 3, color: '#f97316' },
    MEDIUM: { id: 'medium', label: 'متوسط', weight: 2, color: '#eab308' },
    LOW: { id: 'low', label: 'پایین', weight: 1, color: '#22c55e' }
  },
  
  // انواع وابستگی
  DEPENDENCY_TYPES: {
    FINISH_TO_START: { id: 'FS', label: 'پایان به شروع', description: 'تسک B بعد از پایان تسک A شروع می‌شود' },
    START_TO_START: { id: 'SS', label: 'شروع به شروع', description: 'تسک B همزمان با شروع تسک A شروع می‌شود' },
    FINISH_TO_FINISH: { id: 'FF', label: 'پایان به پایان', description: 'تسک B همزمان با پایان تسک A پایان می‌یابد' },
    START_TO_FINISH: { id: 'SF', label: 'شروع به پایان', description: 'تسک B با شروع تسک A پایان می‌یابد' }
  },
  
  // تنظیمات زمان‌بندی
  SCHEDULING: {
    DEFAULT_TASK_DURATION: 1, // روز
    WORKING_HOURS_PER_DAY: 8,
    BUFFER_PERCENTAGE: 20, // درصد بافر برای تسک‌ها
    AUTO_RESCHEDULE: true
  },
  
  // تنظیمات انحراف
  DEVIATION: {
    WARNING_THRESHOLD: 10, // درصد
    CRITICAL_THRESHOLD: 25, // درصد
    AUTO_ALERT: true
  }
};

/**
 * ✅ v17.0 Phase 2: ساختار تسک
 */
const TASK_TEMPLATE = {
  id: '',
  name: '',
  description: '',
  phaseId: '',
  status: 'not_started',
  priority: 'medium',
  assignee: null,
  
  // زمان‌بندی
  estimatedDuration: 1, // روز
  actualDuration: null,
  startDate: null,
  endDate: null,
  actualStartDate: null,
  actualEndDate: null,
  
  // وابستگی‌ها
  dependencies: [], // [{taskId, type: 'FS'}]
  dependents: [], // تسک‌هایی که به این وابسته‌اند
  
  // پیشرفت
  progress: 0,
  completedSubtasks: 0,
  totalSubtasks: 0,
  
  // متادیتا
  tags: [],
  notes: '',
  attachments: [],
  createdAt: null,
  updatedAt: null
};

/**
 * ✅ v17.0 Phase 2: ساختار Milestone
 */
const MILESTONE_TEMPLATE = {
  id: '',
  name: '',
  description: '',
  targetDate: null,
  actualDate: null,
  status: 'pending', // pending, achieved, missed, at_risk
  
  // شرایط تکمیل
  completionCriteria: [], // [{type: 'task_completion', taskIds: [...]}]
  kpis: [], // [{id, name, target, actual, unit}]
  
  // تسک‌های مرتبط
  relatedTasks: [],
  
  // متادیتا
  createdAt: null,
  updatedAt: null
};

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 2: TASK MANAGEMENT SYSTEM
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0 Phase 2: ایجاد تسک جدید
 */
function createTask(projectId, taskData) {
  try {
    Logger.log(`📋 ایجاد تسک جدید برای پروژه ${projectId}`);
    
    const context = loadSmartProjectContext(projectId);
    if (!context) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    // اطمینان از وجود آرایه تسک‌ها
    if (!context.roadmap) {
      context.roadmap = { tasks: [], milestones: [], lastUpdated: null };
    }
    if (!context.roadmap.tasks) {
      context.roadmap.tasks = [];
    }
    
    // ایجاد تسک
    const task = {
      ...TASK_TEMPLATE,
      ...taskData,
      id: taskData.id || `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    
    // اعتبارسنجی وابستگی‌ها
    if (task.dependencies && task.dependencies.length > 0) {
      const validationResult = validateDependencies(context.roadmap.tasks, task);
      if (!validationResult.valid) {
        return { success: false, error: validationResult.error };
      }
    }
    
    // محاسبه تاریخ‌های شروع و پایان
    calculateTaskDates(task, context.roadmap.tasks);
    
    // اضافه کردن به لیست
    context.roadmap.tasks.push(task);
    context.roadmap.lastUpdated = new Date().toISOString();
    
    // به‌روزرسانی dependents تسک‌های دیگر
    updateDependentsList(context.roadmap.tasks);
    
    // ذخیره
    saveSmartProjectContext(projectId, context);
    
    Logger.log(`✅ تسک ${task.id} ایجاد شد`);
    
    return {
      success: true,
      task: task
    };
    
  } catch (error) {
    Logger.log('❌ خطا در ایجاد تسک: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * ✅ v17.0 Phase 2: به‌روزرسانی تسک
 */
function updateTask(projectId, taskId, updates) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context || !context.roadmap || !context.roadmap.tasks) {
      return { success: false, error: 'پروژه یا تسک یافت نشد' };
    }
    
    const taskIndex = context.roadmap.tasks.findIndex(t => t.id === taskId);
    if (taskIndex === -1) {
      return { success: false, error: 'تسک یافت نشد' };
    }
    
    const task = context.roadmap.tasks[taskIndex];
    const oldStatus = task.status;
    
    // اعمال تغییرات
    Object.assign(task, updates, { updatedAt: new Date().toISOString() });
    
    // اگر وضعیت تغییر کرده
    if (updates.status && updates.status !== oldStatus) {
      handleStatusChange(task, oldStatus, updates.status);
    }
    
    // اگر وابستگی‌ها تغییر کرده، اعتبارسنجی کن
    if (updates.dependencies) {
      const validationResult = validateDependencies(
        context.roadmap.tasks.filter(t => t.id !== taskId), 
        task
      );
      if (!validationResult.valid) {
        return { success: false, error: validationResult.error };
      }
    }
    
    // محاسبه مجدد تاریخ‌ها
    recalculateAllDates(context.roadmap.tasks);
    
    // به‌روزرسانی dependents
    updateDependentsList(context.roadmap.tasks);
    
    context.roadmap.lastUpdated = new Date().toISOString();
    saveSmartProjectContext(projectId, context);
    
    // بررسی انحراف
    const deviations = checkDeviations(context.roadmap);
    
    return {
      success: true,
      task: task,
      deviations: deviations
    };
    
  } catch (error) {
    Logger.log('❌ خطا در به‌روزرسانی تسک: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * ✅ v17.0 Phase 2: به‌روزرسانی پیشرفت تسک
 */
function updateTaskProgress(projectId, taskId, progress, notes = '') {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context || !context.roadmap) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    const task = context.roadmap.tasks.find(t => t.id === taskId);
    if (!task) {
      return { success: false, error: 'تسک یافت نشد' };
    }
    
    // به‌روزرسانی پیشرفت
    task.progress = Math.min(100, Math.max(0, progress));
    task.updatedAt = new Date().toISOString();
    
    if (notes) {
      task.notes = (task.notes || '') + `\n[${new Date().toLocaleDateString('fa-IR')}] ${notes}`;
    }
    
    // اگر پیشرفت ۱۰۰٪ شد، وضعیت را تکمیل کن
    if (task.progress === 100 && task.status !== 'completed') {
      task.status = 'completed';
      task.actualEndDate = new Date().toISOString();
      
      // آزادسازی تسک‌های وابسته
      unlockDependentTasks(context.roadmap.tasks, taskId);
    }
    
    // اگر شروع شده ولی وضعیت هنوز شروع نشده است
    if (task.progress > 0 && task.status === 'not_started') {
      task.status = 'in_progress';
      task.actualStartDate = new Date().toISOString();
    }
    
    context.roadmap.lastUpdated = new Date().toISOString();
    saveSmartProjectContext(projectId, context);
    
    // محاسبه پیشرفت کلی
    const overallProgress = calculateOverallProgress(context.roadmap);
    
    // بررسی milestones
    checkMilestones(projectId, context.roadmap);
    
    return {
      success: true,
      task: task,
      overallProgress: overallProgress
    };
    
  } catch (error) {
    Logger.log('❌ خطا در به‌روزرسانی پیشرفت: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * ✅ v17.0 Phase 2: حذف تسک
 */
function deleteTask(projectId, taskId) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context || !context.roadmap) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    // بررسی وابستگی‌های تسک‌های دیگر
    const dependentTasks = context.roadmap.tasks.filter(t => 
      t.dependencies && t.dependencies.some(d => d.taskId === taskId)
    );
    
    if (dependentTasks.length > 0) {
      return {
        success: false,
        error: `این تسک دارای ${dependentTasks.length} تسک وابسته است. ابتدا وابستگی‌ها را حذف کنید.`,
        dependentTasks: dependentTasks.map(t => ({ id: t.id, name: t.name }))
      };
    }
    
    // حذف تسک
    context.roadmap.tasks = context.roadmap.tasks.filter(t => t.id !== taskId);
    context.roadmap.lastUpdated = new Date().toISOString();
    
    saveSmartProjectContext(projectId, context);
    
    return { success: true };
    
  } catch (error) {
    Logger.log('❌ خطا در حذف تسک: ' + error);
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 3: DEPENDENCY MANAGEMENT
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0 Phase 2: اعتبارسنجی وابستگی‌ها
 */
function validateDependencies(existingTasks, newTask) {
  if (!newTask.dependencies || newTask.dependencies.length === 0) {
    return { valid: true };
  }
  
  for (const dep of newTask.dependencies) {
    // بررسی وجود تسک وابسته
    const depTask = existingTasks.find(t => t.id === dep.taskId);
    if (!depTask) {
      return { valid: false, error: `تسک وابسته ${dep.taskId} یافت نشد` };
    }
    
    // بررسی حلقه وابستگی (circular dependency)
    if (hasCircularDependency(existingTasks, newTask.id, dep.taskId)) {
      return { valid: false, error: 'وابستگی حلقوی تشخیص داده شد' };
    }
  }
  
  return { valid: true };
}

/**
 * ✅ v17.0 Phase 2: تشخیص وابستگی حلقوی
 */
function hasCircularDependency(tasks, sourceId, targetId, visited = new Set()) {
  if (sourceId === targetId) return true;
  if (visited.has(targetId)) return false;
  
  visited.add(targetId);
  
  const targetTask = tasks.find(t => t.id === targetId);
  if (!targetTask || !targetTask.dependencies) return false;
  
  for (const dep of targetTask.dependencies) {
    if (hasCircularDependency(tasks, sourceId, dep.taskId, visited)) {
      return true;
    }
  }
  
  return false;
}

/**
 * ✅ v17.0 Phase 2: اضافه کردن وابستگی
 */
function addDependency(projectId, taskId, dependencyTaskId, type = 'FS') {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context || !context.roadmap) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    const task = context.roadmap.tasks.find(t => t.id === taskId);
    const depTask = context.roadmap.tasks.find(t => t.id === dependencyTaskId);
    
    if (!task || !depTask) {
      return { success: false, error: 'تسک یافت نشد' };
    }
    
    // بررسی وابستگی تکراری
    if (task.dependencies && task.dependencies.some(d => d.taskId === dependencyTaskId)) {
      return { success: false, error: 'این وابستگی قبلاً وجود دارد' };
    }
    
    // بررسی حلقوی
    if (hasCircularDependency(context.roadmap.tasks, taskId, dependencyTaskId)) {
      return { success: false, error: 'وابستگی حلقوی ایجاد می‌شود' };
    }
    
    // اضافه کردن وابستگی
    if (!task.dependencies) task.dependencies = [];
    task.dependencies.push({ taskId: dependencyTaskId, type: type });
    
    // به‌روزرسانی dependents
    if (!depTask.dependents) depTask.dependents = [];
    if (!depTask.dependents.includes(taskId)) {
      depTask.dependents.push(taskId);
    }
    
    // محاسبه مجدد تاریخ‌ها
    recalculateAllDates(context.roadmap.tasks);
    
    context.roadmap.lastUpdated = new Date().toISOString();
    saveSmartProjectContext(projectId, context);
    
    return { success: true };
    
  } catch (error) {
    Logger.log('❌ خطا در اضافه کردن وابستگی: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * ✅ v17.0 Phase 2: حذف وابستگی
 */
function removeDependency(projectId, taskId, dependencyTaskId) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context || !context.roadmap) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    const task = context.roadmap.tasks.find(t => t.id === taskId);
    if (!task) {
      return { success: false, error: 'تسک یافت نشد' };
    }
    
    // حذف وابستگی
    if (task.dependencies) {
      task.dependencies = task.dependencies.filter(d => d.taskId !== dependencyTaskId);
    }
    
    // به‌روزرسانی dependents
    const depTask = context.roadmap.tasks.find(t => t.id === dependencyTaskId);
    if (depTask && depTask.dependents) {
      depTask.dependents = depTask.dependents.filter(id => id !== taskId);
    }
    
    // محاسبه مجدد تاریخ‌ها
    recalculateAllDates(context.roadmap.tasks);
    
    context.roadmap.lastUpdated = new Date().toISOString();
    saveSmartProjectContext(projectId, context);
    
    return { success: true };
    
  } catch (error) {
    Logger.log('❌ خطا در حذف وابستگی: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * ✅ v17.0 Phase 2: به‌روزرسانی لیست dependents
 */
function updateDependentsList(tasks) {
  // پاک کردن dependents قبلی
  tasks.forEach(t => t.dependents = []);
  
  // بازسازی
  for (const task of tasks) {
    if (task.dependencies) {
      for (const dep of task.dependencies) {
        const depTask = tasks.find(t => t.id === dep.taskId);
        if (depTask) {
          if (!depTask.dependents) depTask.dependents = [];
          if (!depTask.dependents.includes(task.id)) {
            depTask.dependents.push(task.id);
          }
        }
      }
    }
  }
}

/**
 * ✅ v17.0 Phase 2: آزادسازی تسک‌های وابسته
 */
function unlockDependentTasks(tasks, completedTaskId) {
  for (const task of tasks) {
    if (task.dependencies && task.dependencies.some(d => d.taskId === completedTaskId)) {
      // بررسی آیا همه وابستگی‌ها تکمیل شده‌اند
      const allDepsCompleted = task.dependencies.every(dep => {
        const depTask = tasks.find(t => t.id === dep.taskId);
        return depTask && depTask.status === 'completed';
      });
      
      // اگر تسک مسدود بود و همه وابستگی‌ها تکمیل شدند
      if (allDepsCompleted && task.status === 'blocked') {
        task.status = 'not_started';
        Logger.log(`🔓 تسک ${task.id} آزاد شد`);
      }
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 4: DATE CALCULATION & SCHEDULING
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0 Phase 2: محاسبه تاریخ‌های تسک
 */
function calculateTaskDates(task, allTasks) {
  if (!task.startDate) {
    // اگر وابستگی دارد
    if (task.dependencies && task.dependencies.length > 0) {
      let latestEndDate = null;
      
      for (const dep of task.dependencies) {
        const depTask = allTasks.find(t => t.id === dep.taskId);
        if (depTask && depTask.endDate) {
          const depEndDate = new Date(depTask.endDate);
          if (!latestEndDate || depEndDate > latestEndDate) {
            latestEndDate = depEndDate;
          }
        }
      }
      
      if (latestEndDate) {
        // شروع یک روز بعد از پایان وابستگی
        latestEndDate.setDate(latestEndDate.getDate() + 1);
        task.startDate = latestEndDate.toISOString();
      }
    }
    
    // اگر هنوز تاریخ ندارد، از امروز شروع کن
    if (!task.startDate) {
      task.startDate = new Date().toISOString();
    }
  }
  
  // محاسبه تاریخ پایان
  if (!task.endDate && task.estimatedDuration) {
    const startDate = new Date(task.startDate);
    const endDate = new Date(startDate);
    endDate.setDate(endDate.getDate() + task.estimatedDuration);
    task.endDate = endDate.toISOString();
  }
}

/**
 * ✅ v17.0 Phase 2: محاسبه مجدد همه تاریخ‌ها
 */
function recalculateAllDates(tasks) {
  // مرتب‌سازی توپولوژیک
  const sorted = topologicalSort(tasks);
  
  for (const task of sorted) {
    calculateTaskDates(task, tasks);
  }
}

/**
 * ✅ v17.0 Phase 2: مرتب‌سازی توپولوژیک
 */
function topologicalSort(tasks) {
  const visited = new Set();
  const result = [];
  
  function visit(task) {
    if (visited.has(task.id)) return;
    visited.add(task.id);
    
    // ابتدا وابستگی‌ها را بازدید کن
    if (task.dependencies) {
      for (const dep of task.dependencies) {
        const depTask = tasks.find(t => t.id === dep.taskId);
        if (depTask) visit(depTask);
      }
    }
    
    result.push(task);
  }
  
  for (const task of tasks) {
    visit(task);
  }
  
  return result;
}

/**
 * ✅ v17.0 Phase 2: محاسبه Critical Path
 */
function calculateCriticalPath(tasks) {
  if (!tasks || tasks.length === 0) return [];
  
  // محاسبه ES (Earliest Start) و EF (Earliest Finish) - Forward Pass
  const taskMap = new Map();
  tasks.forEach(t => taskMap.set(t.id, {
    ...t,
    ES: 0, EF: 0, LS: Infinity, LF: Infinity, slack: 0
  }));
  
  const sorted = topologicalSort(tasks);
  
  // Forward Pass
  for (const task of sorted) {
    const t = taskMap.get(task.id);
    
    if (task.dependencies && task.dependencies.length > 0) {
      let maxEF = 0;
      for (const dep of task.dependencies) {
        const depT = taskMap.get(dep.taskId);
        if (depT && depT.EF > maxEF) {
          maxEF = depT.EF;
        }
      }
      t.ES = maxEF;
    }
    
    t.EF = t.ES + (task.estimatedDuration || 1);
  }
  
  // پیدا کردن آخرین EF
  let projectEnd = 0;
  for (const [, t] of taskMap) {
    if (t.EF > projectEnd) projectEnd = t.EF;
  }
  
  // Backward Pass
  for (let i = sorted.length - 1; i >= 0; i--) {
    const task = sorted[i];
    const t = taskMap.get(task.id);
    
    if (!task.dependents || task.dependents.length === 0) {
      t.LF = projectEnd;
    } else {
      let minLS = Infinity;
      for (const depId of task.dependents) {
        const depT = taskMap.get(depId);
        if (depT && depT.LS < minLS) {
          minLS = depT.LS;
        }
      }
      t.LF = minLS;
    }
    
    t.LS = t.LF - (task.estimatedDuration || 1);
    t.slack = t.LS - t.ES;
  }
  
  // تسک‌های روی Critical Path (slack = 0)
  const criticalPath = [];
  for (const [id, t] of taskMap) {
    if (t.slack === 0) {
      criticalPath.push({
        id: id,
        name: t.name,
        duration: t.estimatedDuration || 1,
        ES: t.ES,
        EF: t.EF,
        LS: t.LS,
        LF: t.LF
      });
    }
  }
  
  return criticalPath.sort((a, b) => a.ES - b.ES);
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 5: MILESTONE MANAGEMENT
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0 Phase 2: ایجاد Milestone
 */
function createMilestone(projectId, milestoneData) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    if (!context.roadmap) {
      context.roadmap = { tasks: [], milestones: [], lastUpdated: null };
    }
    if (!context.roadmap.milestones) {
      context.roadmap.milestones = [];
    }
    
    const milestone = {
      ...MILESTONE_TEMPLATE,
      ...milestoneData,
      id: milestoneData.id || `milestone_${Date.now()}`,
      status: 'pending',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    
    context.roadmap.milestones.push(milestone);
    context.roadmap.lastUpdated = new Date().toISOString();
    
    saveSmartProjectContext(projectId, context);
    
    return { success: true, milestone: milestone };
    
  } catch (error) {
    Logger.log('❌ خطا در ایجاد Milestone: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * ✅ v17.0 Phase 2: بررسی Milestones
 */
function checkMilestones(projectId, roadmap) {
  if (!roadmap.milestones) return;
  
  const now = new Date();
  
  for (const milestone of roadmap.milestones) {
    // بررسی شرایط تکمیل
    let achieved = true;
    
    for (const criteria of (milestone.completionCriteria || [])) {
      if (criteria.type === 'task_completion') {
        for (const taskId of (criteria.taskIds || [])) {
          const task = roadmap.tasks.find(t => t.id === taskId);
          if (!task || task.status !== 'completed') {
            achieved = false;
            break;
          }
        }
      } else if (criteria.type === 'progress_threshold') {
        const progress = calculateOverallProgress(roadmap);
        if (progress < criteria.threshold) {
          achieved = false;
        }
      }
      
      if (!achieved) break;
    }
    
    // به‌روزرسانی وضعیت
    if (achieved && milestone.status === 'pending') {
      milestone.status = 'achieved';
      milestone.actualDate = now.toISOString();
      Logger.log(`🏆 Milestone "${milestone.name}" تکمیل شد!`);
    } else if (!achieved && milestone.targetDate) {
      const targetDate = new Date(milestone.targetDate);
      if (now > targetDate) {
        milestone.status = 'missed';
      } else {
        // بررسی ریسک
        const daysRemaining = Math.ceil((targetDate - now) / (1000 * 60 * 60 * 24));
        const incompleteTasks = (milestone.relatedTasks || []).filter(taskId => {
          const task = roadmap.tasks.find(t => t.id === taskId);
          return task && task.status !== 'completed';
        });
        
        if (incompleteTasks.length > daysRemaining) {
          milestone.status = 'at_risk';
        }
      }
    }
    
    milestone.updatedAt = now.toISOString();
  }
}

/**
 * ✅ v17.0 Phase 2: به‌روزرسانی KPI
 */
function updateKPI(projectId, milestoneId, kpiId, actualValue) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context || !context.roadmap) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    const milestone = context.roadmap.milestones.find(m => m.id === milestoneId);
    if (!milestone) {
      return { success: false, error: 'Milestone یافت نشد' };
    }
    
    const kpi = milestone.kpis.find(k => k.id === kpiId);
    if (!kpi) {
      return { success: false, error: 'KPI یافت نشد' };
    }
    
    kpi.actual = actualValue;
    kpi.updatedAt = new Date().toISOString();
    
    // محاسبه درصد تحقق
    kpi.achievement = kpi.target ? Math.round((actualValue / kpi.target) * 100) : 0;
    
    context.roadmap.lastUpdated = new Date().toISOString();
    saveSmartProjectContext(projectId, context);
    
    return { success: true, kpi: kpi };
    
  } catch (error) {
    Logger.log('❌ خطا در به‌روزرسانی KPI: ' + error);
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 6: DEVIATION DETECTION & MONITORING
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0 Phase 2: تشخیص انحراف‌ها
 */
function checkDeviations(roadmap) {
  const deviations = [];
  const now = new Date();
  
  for (const task of (roadmap.tasks || [])) {
    // بررسی تأخیر
    if (task.endDate && task.status !== 'completed') {
      const endDate = new Date(task.endDate);
      if (now > endDate) {
        const daysLate = Math.ceil((now - endDate) / (1000 * 60 * 60 * 24));
        deviations.push({
          type: 'delay',
          severity: daysLate > 7 ? 'critical' : daysLate > 3 ? 'warning' : 'info',
          taskId: task.id,
          taskName: task.name,
          message: `${daysLate} روز تأخیر`,
          daysLate: daysLate
        });
      }
    }
    
    // بررسی پیشرفت مورد انتظار
    if (task.startDate && task.endDate && task.status === 'in_progress') {
      const startDate = new Date(task.startDate);
      const endDate = new Date(task.endDate);
      const totalDuration = endDate - startDate;
      const elapsed = now - startDate;
      const expectedProgress = Math.min(100, Math.round((elapsed / totalDuration) * 100));
      
      const progressGap = expectedProgress - (task.progress || 0);
      
      if (progressGap > DYNAMIC_ROADMAP_CONFIG.DEVIATION.CRITICAL_THRESHOLD) {
        deviations.push({
          type: 'progress_lag',
          severity: 'critical',
          taskId: task.id,
          taskName: task.name,
          message: `پیشرفت ${progressGap}% کمتر از انتظار`,
          expectedProgress: expectedProgress,
          actualProgress: task.progress || 0
        });
      } else if (progressGap > DYNAMIC_ROADMAP_CONFIG.DEVIATION.WARNING_THRESHOLD) {
        deviations.push({
          type: 'progress_lag',
          severity: 'warning',
          taskId: task.id,
          taskName: task.name,
          message: `پیشرفت ${progressGap}% کمتر از انتظار`,
          expectedProgress: expectedProgress,
          actualProgress: task.progress || 0
        });
      }
    }
    
    // بررسی تسک‌های مسدود شده
    if (task.status === 'blocked') {
      deviations.push({
        type: 'blocked',
        severity: 'warning',
        taskId: task.id,
        taskName: task.name,
        message: 'تسک مسدود شده',
        blockedBy: task.dependencies?.map(d => d.taskId) || []
      });
    }
  }
  
  return deviations;
}

/**
 * ✅ v17.0 Phase 2: محاسبه پیشرفت کلی
 */
function calculateOverallProgress(roadmap) {
  if (!roadmap.tasks || roadmap.tasks.length === 0) return 0;
  
  let totalWeight = 0;
  let completedWeight = 0;
  
  for (const task of roadmap.tasks) {
    const weight = DYNAMIC_ROADMAP_CONFIG.PRIORITY[task.priority?.toUpperCase()]?.weight || 2;
    totalWeight += weight;
    completedWeight += (weight * (task.progress || 0)) / 100;
  }
  
  return totalWeight > 0 ? Math.round((completedWeight / totalWeight) * 100) : 0;
}

/**
 * ✅ v17.0 Phase 2: مدیریت تغییر وضعیت
 */
function handleStatusChange(task, oldStatus, newStatus) {
  const now = new Date().toISOString();
  
  if (newStatus === 'in_progress' && !task.actualStartDate) {
    task.actualStartDate = now;
  }
  
  if (newStatus === 'completed') {
    task.actualEndDate = now;
    task.progress = 100;
  }
  
  // ثبت در تاریخچه
  if (!task.statusHistory) task.statusHistory = [];
  task.statusHistory.push({
    from: oldStatus,
    to: newStatus,
    timestamp: now
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 7: GANTT CHART GENERATION
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0 Phase 2: تولید نمودار Gantt
 */
function generateGanttChart(roadmap) {
  if (!roadmap || !roadmap.tasks || roadmap.tasks.length === 0) {
    return 'gantt\n  title نقشه راه پروژه\n  dateFormat YYYY-MM-DD\n  section بدون تسک\n    هیچ تسکی تعریف نشده :a1, 2024-01-01, 1d';
  }
  
  let mermaid = 'gantt\n';
  mermaid += '  title نقشه راه پروژه\n';
  mermaid += '  dateFormat YYYY-MM-DD\n';
  mermaid += '  excludes weekends\n\n';
  
  // گروه‌بندی بر اساس فاز
  const phases = {};
  for (const task of roadmap.tasks) {
    const phase = task.phaseId || 'general';
    if (!phases[phase]) phases[phase] = [];
    phases[phase].push(task);
  }
  
  // تولید برای هر فاز
  for (const [phase, tasks] of Object.entries(phases)) {
    const phaseName = phase === 'general' ? 'عمومی' : phase;
    mermaid += `  section ${phaseName}\n`;
    
    for (const task of tasks) {
      const startDate = task.startDate ? new Date(task.startDate).toISOString().split('T')[0] : new Date().toISOString().split('T')[0];
      const duration = task.estimatedDuration || 1;
      const status = getGanttStatus(task);
      const deps = task.dependencies?.map(d => d.taskId).join(', ') || '';
      
      // فرمت: نام :وضعیت, شناسه, after dep1 dep2, تاریخ, مدت
      if (deps) {
        mermaid += `    ${task.name} :${status}, ${task.id}, after ${deps}, ${duration}d\n`;
      } else {
        mermaid += `    ${task.name} :${status}, ${task.id}, ${startDate}, ${duration}d\n`;
      }
    }
    
    mermaid += '\n';
  }
  
  // اضافه کردن Milestones
  if (roadmap.milestones && roadmap.milestones.length > 0) {
    mermaid += '  section نقاط عطف\n';
    for (const ms of roadmap.milestones) {
      const date = ms.targetDate ? new Date(ms.targetDate).toISOString().split('T')[0] : new Date().toISOString().split('T')[0];
      const status = ms.status === 'achieved' ? 'done' : ms.status === 'missed' ? 'crit' : '';
      mermaid += `    ${ms.name} :${status}milestone, ${ms.id}, ${date}, 0d\n`;
    }
  }
  
  return mermaid;
}

/**
 * ✅ v17.0 Phase 2: وضعیت Gantt
 */
function getGanttStatus(task) {
  switch (task.status) {
    case 'completed': return 'done, ';
    case 'in_progress': return 'active, ';
    case 'blocked': return 'crit, ';
    default: return '';
  }
}

/**
 * ✅ v17.0 Phase 2: تولید نمودار وابستگی‌ها
 */
function generateDependencyGraph(roadmap) {
  if (!roadmap || !roadmap.tasks || roadmap.tasks.length === 0) {
    return 'graph LR\n  A[بدون تسک]';
  }
  
  let mermaid = 'graph LR\n';
  mermaid += '  %% نمودار وابستگی تسک‌ها\n\n';
  
  // تعریف نودها
  for (const task of roadmap.tasks) {
    const shape = task.status === 'completed' ? '([' : task.status === 'in_progress' ? '{{' : '[';
    const closeShape = task.status === 'completed' ? '])' : task.status === 'in_progress' ? '}}' : ']';
    const icon = DYNAMIC_ROADMAP_CONFIG.TASK_STATUS[task.status?.toUpperCase()]?.icon || '⏳';
    mermaid += `  ${task.id}${shape}"${icon} ${task.name}"${closeShape}\n`;
  }
  
  mermaid += '\n  %% وابستگی‌ها\n';
  
  // تعریف اتصالات
  for (const task of roadmap.tasks) {
    if (task.dependencies) {
      for (const dep of task.dependencies) {
        const depType = DYNAMIC_ROADMAP_CONFIG.DEPENDENCY_TYPES[dep.type];
        const label = depType?.id || 'FS';
        mermaid += `  ${dep.taskId} -->|${label}| ${task.id}\n`;
      }
    }
  }
  
  // استایل‌ها
  mermaid += '\n  %% استایل‌ها\n';
  for (const task of roadmap.tasks) {
    const color = DYNAMIC_ROADMAP_CONFIG.TASK_STATUS[task.status?.toUpperCase()]?.color || '#9ca3af';
    mermaid += `  style ${task.id} fill:${color}20,stroke:${color}\n`;
  }
  
  return mermaid;
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 8: AUTOMATIC TASK GENERATION
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0 Phase 2: تولید خودکار تسک‌ها از فازها
 */
function generateTasksFromPhases(projectId) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context || !context.phases) {
      return { success: false, error: 'پروژه یا فازها یافت نشد' };
    }
    
    if (!context.roadmap) {
      context.roadmap = { tasks: [], milestones: [], lastUpdated: null };
    }
    
    const tasks = [];
    let previousTaskId = null;
    
    for (const phase of context.phases) {
      // تسک اصلی فاز
      const phaseTask = {
        ...TASK_TEMPLATE,
        id: `task_phase_${phase.id}`,
        name: phase.name,
        description: phase.description || '',
        phaseId: phase.id,
        status: phase.status === 'completed' ? 'completed' : 
                phase.status === 'in_progress' ? 'in_progress' : 'not_started',
        priority: 'high',
        estimatedDuration: 3,
        progress: phase.progress || 0,
        dependencies: previousTaskId ? [{ taskId: previousTaskId, type: 'FS' }] : [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      };
      
      tasks.push(phaseTask);
      previousTaskId = phaseTask.id;
      
      // ایجاد Milestone برای هر فاز
      const milestone = {
        ...MILESTONE_TEMPLATE,
        id: `milestone_${phase.id}`,
        name: `تکمیل ${phase.name}`,
        relatedTasks: [phaseTask.id],
        completionCriteria: [{ type: 'task_completion', taskIds: [phaseTask.id] }],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      };
      
      if (!context.roadmap.milestones) context.roadmap.milestones = [];
      context.roadmap.milestones.push(milestone);
    }
    
    // محاسبه تاریخ‌ها
    recalculateAllDates(tasks);
    
    context.roadmap.tasks = tasks;
    context.roadmap.lastUpdated = new Date().toISOString();
    
    saveSmartProjectContext(projectId, context);
    
    return {
      success: true,
      tasksCount: tasks.length,
      milestonesCount: context.roadmap.milestones.length
    };
    
  } catch (error) {
    Logger.log('❌ خطا در تولید تسک‌ها: ' + error);
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// ✅ v17.2: API آمار Smart Projects برای داشبورد
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.2: دریافت آمار کلی Smart Projects
 * @returns {Object} آمار پروژه‌ها، تسک‌ها، مکالمات و توکن‌ها
 */
function apiGetSmartProjectsStats() {
  try {
    const registry = getPersistentProjectRegistry();
    const projectIds = Object.keys(registry);
    
    let stats = {
      totalProjects: projectIds.length,
      activeProjects: 0,
      completedProjects: 0,
      totalTasks: 0,
      completedTasks: 0,
      inProgressTasks: 0,
      totalConversations: 0,
      totalTokens: 0,
      totalCost: 0
    };
    
    for (const projectId of projectIds) {
      try {
        const context = loadSmartProjectContext(projectId);
        if (!context) continue;
        
        // وضعیت پروژه
        const projectStatus = context.status || 'active';
        if (projectStatus === 'completed') {
          stats.completedProjects++;
        } else if (projectStatus === 'active' || projectStatus === 'in_progress') {
          stats.activeProjects++;
        }
        
        // تسک‌ها
        const tasks = context.roadmap?.tasks || [];
        stats.totalTasks += tasks.length;
        stats.completedTasks += tasks.filter(t => t.status === 'completed').length;
        stats.inProgressTasks += tasks.filter(t => t.status === 'in_progress').length;
        
        // مکالمات
        const conversations = context.conversations || [];
        stats.totalConversations += conversations.length;
        
        // متریک‌ها
        const metrics = context.metrics || {};
        stats.totalTokens += metrics.totalTokens || 0;
        stats.totalCost += metrics.totalCost || 0;
        
      } catch (projectError) {
        Logger.log('Error processing project ' + projectId + ': ' + projectError);
      }
    }
    
    // اگر پروژه فعالی نیست، حداقل تعداد پروژه‌ها رو نشون بده
    if (stats.activeProjects === 0 && projectIds.length > 0) {
      stats.activeProjects = projectIds.length;
    }
    
    return {
      success: true,
      stats: stats
    };
    
  } catch (error) {
    Logger.log('❌ Error in apiGetSmartProjectsStats: ' + error);
    return {
      success: false,
      error: error.message,
      stats: {
        totalProjects: 0,
        activeProjects: 0,
        completedProjects: 0,
        totalTasks: 0,
        completedTasks: 0,
        inProgressTasks: 0,
        totalConversations: 0,
        totalTokens: 0,
        totalCost: 0
      }
    };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 9: API ENDPOINTS FOR PHASE 2
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0 Phase 2: API - دریافت نقشه راه کامل
 */
function apiGetRoadmap(projectId) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    const roadmap = context.roadmap || { tasks: [], milestones: [] };
    
    return {
      success: true,
      roadmap: {
        tasks: roadmap.tasks || [],
        milestones: roadmap.milestones || [],
        lastUpdated: roadmap.lastUpdated,
        overallProgress: calculateOverallProgress(roadmap),
        deviations: checkDeviations(roadmap),
        criticalPath: calculateCriticalPath(roadmap.tasks || []),
        ganttChart: generateGanttChart(roadmap),
        dependencyGraph: generateDependencyGraph(roadmap)
      }
    };
    
  } catch (error) {
    Logger.log('❌ خطا در دریافت نقشه راه: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * ✅ v17.0 Phase 2: API - ایجاد تسک
 */
function apiCreateTask(projectId, taskData) {
  return createTask(projectId, taskData);
}

/**
 * ✅ v17.0 Phase 2: API - به‌روزرسانی تسک
 */
function apiUpdateTask(projectId, taskId, updates) {
  return updateTask(projectId, taskId, updates);
}

/**
 * ✅ v17.0 Phase 2: API - به‌روزرسانی پیشرفت
 */
function apiUpdateTaskProgress(projectId, taskId, progress, notes) {
  return updateTaskProgress(projectId, taskId, progress, notes);
}

/**
 * ✅ v17.0 Phase 2: API - حذف تسک
 */
function apiDeleteTask(projectId, taskId) {
  return deleteTask(projectId, taskId);
}

/**
 * ✅ v17.0 Phase 2: API - اضافه کردن وابستگی
 */
function apiAddDependency(projectId, taskId, dependencyTaskId, type) {
  return addDependency(projectId, taskId, dependencyTaskId, type || 'FS');
}

/**
 * ✅ v17.0 Phase 2: API - حذف وابستگی
 */
function apiRemoveDependency(projectId, taskId, dependencyTaskId) {
  return removeDependency(projectId, taskId, dependencyTaskId);
}

/**
 * ✅ v17.0 Phase 2: API - ایجاد Milestone
 */
function apiCreateMilestone(projectId, milestoneData) {
  return createMilestone(projectId, milestoneData);
}

/**
 * ✅ v17.0 Phase 2: API - به‌روزرسانی KPI
 */
function apiUpdateKPI(projectId, milestoneId, kpiId, actualValue) {
  return updateKPI(projectId, milestoneId, kpiId, actualValue);
}

/**
 * ✅ v17.0 Phase 2: API - تولید تسک از فازها
 */
function apiGenerateTasksFromPhases(projectId) {
  return generateTasksFromPhases(projectId);
}

/**
 * ✅ v17.0 Phase 2: API - دریافت نمودار Gantt
 */
function apiGetGanttChart(projectId) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    return {
      success: true,
      gantt: generateGanttChart(context.roadmap || { tasks: [], milestones: [] })
    };
    
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * ✅ v17.0 Phase 2: API - دریافت انحراف‌ها
 */
function apiGetDeviations(projectId) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    return {
      success: true,
      deviations: checkDeviations(context.roadmap || { tasks: [] })
    };
    
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * ✅ v17.0 Phase 2: API - دریافت Critical Path
 */
function apiGetCriticalPath(projectId) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context || !context.roadmap) {
      return { success: false, error: 'پروژه یافت نشد' };
    }
    
    return {
      success: true,
      criticalPath: calculateCriticalPath(context.roadmap.tasks || [])
    };
    
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 END OF PHASE 2 - DYNAMIC ROADMAP SYSTEM
// ═══════════════════════════════════════════════════════════════════════════════
// ═══════════════════════════════════════════════════════════════════════════════
// ╔═══════════════════════════════════════════════════════════════════════════════╗
// ║  🧠 اتاق فکر مهندسی هوشمند - فاز ۳                                            ║
// ║  نسخه: 17.0 - INCREMENTAL LEARNING SYSTEM                                     ║
// ╠═══════════════════════════════════════════════════════════════════════════════╣
// ║  ✅ پایگاه دانش پروژه‌محور (Knowledge Base)                                   ║
// ║  ✅ استخراج قواعد و الگوها (Pattern Extraction)                               ║
// ║  ✅ یادگیری از آموزش کاربر (User Training)                                    ║
// ║  ✅ ردیابی پیشرفت نسبت به معیارها (Benchmark Tracking)                        ║
// ║  ✅ رابط‌های تطبیقی (Adaptive Interfaces)                                     ║
// ║  ✅ پیشنهادات هوشمند (Smart Suggestions)                                      ║
// ╚═══════════════════════════════════════════════════════════════════════════════╝

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 1: KNOWLEDGE BASE CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0 Phase 3: تنظیمات سیستم دانش
 */
const KNOWLEDGE_BASE_CONFIG = {
  // انواع دانش
  KNOWLEDGE_TYPES: {
    PATTERN: { id: 'pattern', label: 'الگو', icon: '🔄' },
    RULE: { id: 'rule', label: 'قاعده', icon: '📏' },
    SOLUTION: { id: 'solution', label: 'راه‌حل', icon: '💡' },
    BEST_PRACTICE: { id: 'best_practice', label: 'بهترین روش', icon: '⭐' },
    WARNING: { id: 'warning', label: 'هشدار', icon: '⚠️' },
    TEMPLATE: { id: 'template', label: 'قالب', icon: '📋' },
    SNIPPET: { id: 'snippet', label: 'قطعه کد', icon: '💻' }
  },
  
  // منابع دانش
  KNOWLEDGE_SOURCES: {
    USER_TRAINING: 'user_training',
    AUTO_EXTRACTED: 'auto_extracted',
    PROJECT_ANALYSIS: 'project_analysis',
    ERROR_RESOLUTION: 'error_resolution',
    IMPORTED: 'imported'
  },
  
  // دسته‌بندی‌ها
  CATEGORIES: {
    ARCHITECTURE: { id: 'architecture', label: 'معماری', icon: '🏗️' },
    CODE_QUALITY: { id: 'code_quality', label: 'کیفیت کد', icon: '✨' },
    PERFORMANCE: { id: 'performance', label: 'عملکرد', icon: '⚡' },
    SECURITY: { id: 'security', label: 'امنیت', icon: '🔒' },
    DEPLOYMENT: { id: 'deployment', label: 'استقرار', icon: '🚀' },
    TESTING: { id: 'testing', label: 'تست', icon: '🧪' },
    DATABASE: { id: 'database', label: 'دیتابیس', icon: '💾' },
    API: { id: 'api', label: 'API', icon: '🔌' },
    UI_UX: { id: 'ui_ux', label: 'رابط کاربری', icon: '🎨' },
    DEVOPS: { id: 'devops', label: 'DevOps', icon: '⚙️' }
  },
  
  // تنظیمات امتیازدهی
  SCORING: {
    INITIAL_SCORE: 1.0,
    USE_BOOST: 0.1,
    SUCCESS_BOOST: 0.2,
    FAILURE_PENALTY: -0.15,
    DECAY_RATE: 0.01, // کاهش روزانه
    MIN_SCORE: 0.1,
    MAX_SCORE: 5.0
  },
  
  // تنظیمات استخراج
  EXTRACTION: {
    MIN_PATTERN_OCCURRENCES: 2,
    SIMILARITY_THRESHOLD: 0.7,
    MAX_RULES_PER_PROJECT: 50
  }
};

/**
 * ✅ v17.0 Phase 3: ساختار آیتم دانش
 */
const KNOWLEDGE_ITEM_TEMPLATE = {
  id: '',
  type: 'pattern', // pattern, rule, solution, best_practice, warning, template, snippet
  title: '',
  description: '',
  content: '', // محتوای اصلی (کد، قاعده، توضیح)
  category: '',
  tags: [],
  
  // متادیتا
  source: 'user_training',
  projectId: null, // پروژه منبع
  language: null, // زبان برنامه‌نویسی
  platform: null, // پلتفرم
  
  // امتیازدهی و اعتماد
  score: 1.0,
  confidence: 1.0,
  usageCount: 0,
  successCount: 0,
  failureCount: 0,
  
  // شرایط و زمینه
  conditions: [], // شرایط اعمال
  context: {}, // زمینه استفاده
  examples: [], // مثال‌ها
  relatedItems: [], // آیتم‌های مرتبط
  
  // تاریخچه
  createdAt: null,
  updatedAt: null,
  lastUsedAt: null
};

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 2: KNOWLEDGE BASE CORE FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0 Phase 3: دریافت یا ایجاد پایگاه دانش
 */
function getOrCreateKnowledgeBase() {
  const props = PropertiesService.getScriptProperties();
  let kb = props.getProperty('KNOWLEDGE_BASE');
  
  if (!kb) {
    const newKB = {
      version: '1.0',
      items: [],
      patterns: {},
      statistics: {
        totalItems: 0,
        totalUsage: 0,
        lastUpdated: null
      },
      createdAt: new Date().toISOString()
    };
    props.setProperty('KNOWLEDGE_BASE', JSON.stringify(newKB));
    return newKB;
  }
  
  return JSON.parse(kb);
}

/**
 * ✅ v17.0 Phase 3: ذخیره پایگاه دانش
 */
function saveKnowledgeBase(kb) {
  kb.statistics.lastUpdated = new Date().toISOString();
  kb.statistics.totalItems = kb.items.length;
  PropertiesService.getScriptProperties().setProperty('KNOWLEDGE_BASE', JSON.stringify(kb));
}

/**
 * ✅ v17.0 Phase 3: اضافه کردن آیتم دانش
 */
function addKnowledgeItem(itemData) {
  try {
    const kb = getOrCreateKnowledgeBase();
    
    // بررسی تکراری نبودن
    const exists = kb.items.find(item => 
      item.title === itemData.title && item.type === itemData.type
    );
    
    if (exists) {
      // به‌روزرسانی موجود
      Object.assign(exists, itemData, {
        updatedAt: new Date().toISOString(),
        usageCount: exists.usageCount + 1
      });
    } else {
      // ایجاد جدید
      const newItem = {
        ...KNOWLEDGE_ITEM_TEMPLATE,
        ...itemData,
        id: `kb_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        score: KNOWLEDGE_BASE_CONFIG.SCORING.INITIAL_SCORE,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      };
      
      kb.items.push(newItem);
    }
    
    saveKnowledgeBase(kb);
    
    return { success: true, item: exists || kb.items[kb.items.length - 1] };
    
  } catch (error) {
    Logger.log('❌ خطا در اضافه کردن دانش: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * ✅ v17.0 Phase 3: جستجوی دانش
 */
function searchKnowledge(query, filters = {}) {
  try {
    const kb = getOrCreateKnowledgeBase();
    let results = [...kb.items];
    
    // فیلتر بر اساس نوع
    if (filters.type) {
      results = results.filter(item => item.type === filters.type);
    }
    
    // فیلتر بر اساس دسته
    if (filters.category) {
      results = results.filter(item => item.category === filters.category);
    }
    
    // فیلتر بر اساس زبان
    if (filters.language) {
      results = results.filter(item => !item.language || item.language === filters.language);
    }
    
    // فیلتر بر اساس پلتفرم
    if (filters.platform) {
      results = results.filter(item => !item.platform || item.platform === filters.platform);
    }
    
    // جستجوی متنی
    if (query) {
      const queryLower = query.toLowerCase();
      const queryWords = queryLower.split(/\s+/);
      
      results = results.map(item => {
        let matchScore = 0;
        const searchableText = `${item.title} ${item.description} ${item.content} ${item.tags.join(' ')}`.toLowerCase();
        
        for (const word of queryWords) {
          if (searchableText.includes(word)) {
            matchScore += 1;
            // امتیاز بیشتر برای تطابق در عنوان
            if (item.title.toLowerCase().includes(word)) matchScore += 2;
            // امتیاز بیشتر برای تطابق در تگ‌ها
            if (item.tags.some(t => t.toLowerCase().includes(word))) matchScore += 1;
          }
        }
        
        return { ...item, matchScore };
      }).filter(item => item.matchScore > 0);
    }
    
    // مرتب‌سازی بر اساس امتیاز و تطابق
    results.sort((a, b) => {
      const scoreA = (a.matchScore || 0) * 10 + a.score;
      const scoreB = (b.matchScore || 0) * 10 + b.score;
      return scoreB - scoreA;
    });
    
    // محدود کردن نتایج
    const limit = filters.limit || 20;
    results = results.slice(0, limit);
    
    return { success: true, results, total: results.length };
    
  } catch (error) {
    Logger.log('❌ خطا در جستجوی دانش: ' + error);
    return { success: false, error: error.message, results: [] };
  }
}

/**
 * ✅ v17.0 Phase 3: به‌روزرسانی امتیاز دانش
 */
function updateKnowledgeScore(itemId, action) {
  try {
    const kb = getOrCreateKnowledgeBase();
    const item = kb.items.find(i => i.id === itemId);
    
    if (!item) {
      return { success: false, error: 'آیتم یافت نشد' };
    }
    
    const config = KNOWLEDGE_BASE_CONFIG.SCORING;
    
    switch (action) {
      case 'use':
        item.usageCount++;
        item.score = Math.min(config.MAX_SCORE, item.score + config.USE_BOOST);
        item.lastUsedAt = new Date().toISOString();
        break;
      case 'success':
        item.successCount++;
        item.score = Math.min(config.MAX_SCORE, item.score + config.SUCCESS_BOOST);
        item.confidence = Math.min(1.0, item.confidence + 0.05);
        break;
      case 'failure':
        item.failureCount++;
        item.score = Math.max(config.MIN_SCORE, item.score + config.FAILURE_PENALTY);
        item.confidence = Math.max(0.1, item.confidence - 0.1);
        break;
    }
    
    item.updatedAt = new Date().toISOString();
    kb.statistics.totalUsage++;
    
    saveKnowledgeBase(kb);
    
    return { success: true, item };
    
  } catch (error) {
    Logger.log('❌ خطا در به‌روزرسانی امتیاز: ' + error);
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 3: PATTERN EXTRACTION ENGINE
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0 Phase 3: استخراج الگوها از کد
 */
function extractPatternsFromCode(code, language) {
  const patterns = [];
  
  // الگوهای معماری
  const architecturePatterns = detectArchitecturePatterns(code, language);
  patterns.push(...architecturePatterns);
  
  // الگوهای طراحی
  const designPatterns = detectDesignPatterns(code, language);
  patterns.push(...designPatterns);
  
  // الگوهای کدنویسی
  const codingPatterns = detectCodingPatterns(code, language);
  patterns.push(...codingPatterns);
  
  // الگوهای خطا
  const antiPatterns = detectAntiPatterns(code, language);
  patterns.push(...antiPatterns);
  
  return patterns;
}

/**
 * ✅ v17.0 Phase 3: تشخیص الگوهای معماری
 */
function detectArchitecturePatterns(code, language) {
  const patterns = [];
  
  // MVC Pattern
  if (/class\s+\w*(Controller|View|Model)/i.test(code)) {
    patterns.push({
      type: 'pattern',
      title: 'الگوی MVC',
      description: 'استفاده از الگوی Model-View-Controller',
      category: 'architecture',
      confidence: 0.8,
      tags: ['mvc', 'architecture', 'design-pattern']
    });
  }
  
  // Repository Pattern
  if (/class\s+\w*Repository/i.test(code) || /interface\s+\w*Repository/i.test(code)) {
    patterns.push({
      type: 'pattern',
      title: 'الگوی Repository',
      description: 'استفاده از لایه Repository برای دسترسی به داده',
      category: 'architecture',
      confidence: 0.9,
      tags: ['repository', 'data-access', 'architecture']
    });
  }
  
  // Service Layer
  if (/class\s+\w*Service/i.test(code)) {
    patterns.push({
      type: 'pattern',
      title: 'لایه سرویس',
      description: 'استفاده از لایه سرویس برای منطق کسب‌وکار',
      category: 'architecture',
      confidence: 0.85,
      tags: ['service', 'business-logic', 'architecture']
    });
  }
  
  // Middleware Pattern
  if (/middleware|interceptor/i.test(code)) {
    patterns.push({
      type: 'pattern',
      title: 'الگوی Middleware',
      description: 'استفاده از Middleware برای پردازش درخواست‌ها',
      category: 'architecture',
      confidence: 0.75,
      tags: ['middleware', 'interceptor', 'request-processing']
    });
  }
  
  return patterns;
}

/**
 * ✅ v17.0 Phase 3: تشخیص الگوهای طراحی
 */
function detectDesignPatterns(code, language) {
  const patterns = [];
  
  // Singleton
  if (/getInstance|_instance|private\s+static/i.test(code)) {
    patterns.push({
      type: 'pattern',
      title: 'الگوی Singleton',
      description: 'تضمین وجود فقط یک نمونه از کلاس',
      category: 'code_quality',
      confidence: 0.7,
      tags: ['singleton', 'design-pattern', 'creational']
    });
  }
  
  // Factory
  if (/create\w+|factory|Factory/i.test(code)) {
    patterns.push({
      type: 'pattern',
      title: 'الگوی Factory',
      description: 'استفاده از Factory برای ایجاد اشیا',
      category: 'code_quality',
      confidence: 0.65,
      tags: ['factory', 'design-pattern', 'creational']
    });
  }
  
  // Observer
  if (/addEventListener|on\w+|subscribe|observer/i.test(code)) {
    patterns.push({
      type: 'pattern',
      title: 'الگوی Observer',
      description: 'استفاده از الگوی Observer برای رویدادها',
      category: 'code_quality',
      confidence: 0.75,
      tags: ['observer', 'event', 'design-pattern']
    });
  }
  
  // Decorator
  if (/@\w+|decorator/i.test(code)) {
    patterns.push({
      type: 'pattern',
      title: 'الگوی Decorator',
      description: 'استفاده از Decorator برای گسترش قابلیت‌ها',
      category: 'code_quality',
      confidence: 0.7,
      tags: ['decorator', 'design-pattern', 'structural']
    });
  }
  
  return patterns;
}

/**
 * ✅ v17.0 Phase 3: تشخیص الگوهای کدنویسی
 */
function detectCodingPatterns(code, language) {
  const patterns = [];
  
  // Error Handling
  if (/try\s*{[\s\S]*catch|\.catch\(|onError/i.test(code)) {
    patterns.push({
      type: 'best_practice',
      title: 'مدیریت خطا',
      description: 'استفاده صحیح از try-catch برای مدیریت خطاها',
      category: 'code_quality',
      confidence: 0.9,
      tags: ['error-handling', 'try-catch', 'best-practice']
    });
  }
  
  // Async/Await
  if (/async\s+function|await\s+/i.test(code)) {
    patterns.push({
      type: 'pattern',
      title: 'Async/Await',
      description: 'استفاده از async/await برای عملیات غیرهمزمان',
      category: 'code_quality',
      confidence: 0.95,
      tags: ['async', 'await', 'asynchronous']
    });
  }
  
  // Input Validation
  if (/validate|isValid|check\w*Input|sanitize/i.test(code)) {
    patterns.push({
      type: 'best_practice',
      title: 'اعتبارسنجی ورودی',
      description: 'بررسی و اعتبارسنجی ورودی‌های کاربر',
      category: 'security',
      confidence: 0.85,
      tags: ['validation', 'input', 'security']
    });
  }
  
  // Logging
  if (/Logger\.|console\.(log|error|warn)|log\(/i.test(code)) {
    patterns.push({
      type: 'pattern',
      title: 'لاگ‌گیری',
      description: 'استفاده از سیستم لاگ‌گیری',
      category: 'devops',
      confidence: 0.8,
      tags: ['logging', 'debug', 'monitoring']
    });
  }
  
  // Configuration Management
  if (/config|CONFIG|getProperty|environment/i.test(code)) {
    patterns.push({
      type: 'best_practice',
      title: 'مدیریت پیکربندی',
      description: 'جداسازی تنظیمات از کد',
      category: 'architecture',
      confidence: 0.75,
      tags: ['config', 'configuration', 'environment']
    });
  }
  
  return patterns;
}

/**
 * ✅ v17.0 Phase 3: تشخیص Anti-Patterns
 */
function detectAntiPatterns(code, language) {
  const warnings = [];
  
  // Hardcoded Credentials
  if (/password\s*=\s*['"][^'"]+['"]|api[_-]?key\s*=\s*['"][^'"]+['"]/i.test(code)) {
    warnings.push({
      type: 'warning',
      title: 'اطلاعات حساس در کد',
      description: 'رمز عبور یا کلید API به صورت مستقیم در کد نوشته شده',
      category: 'security',
      confidence: 0.95,
      tags: ['security', 'credentials', 'hardcoded']
    });
  }
  
  // God Class
  const functionCount = (code.match(/function\s+\w+/g) || []).length;
  if (functionCount > 30) {
    warnings.push({
      type: 'warning',
      title: 'کلاس/فایل خیلی بزرگ',
      description: `این فایل ${functionCount} تابع دارد. پیشنهاد: تقسیم به فایل‌های کوچکتر`,
      category: 'code_quality',
      confidence: 0.7,
      tags: ['god-class', 'refactoring', 'maintainability']
    });
  }
  
  // Magic Numbers
  if (/[^a-zA-Z_](?:100|1000|60|24|365|3600)[^0-9]/g.test(code)) {
    warnings.push({
      type: 'warning',
      title: 'اعداد جادویی',
      description: 'استفاده از اعداد بدون توضیح. پیشنهاد: استفاده از ثابت‌های نام‌گذاری شده',
      category: 'code_quality',
      confidence: 0.5,
      tags: ['magic-numbers', 'constants', 'readability']
    });
  }
  
  // Long Functions
  const lines = code.split('\n');
  let currentFunctionLines = 0;
  let inFunction = false;
  
  for (const line of lines) {
    if (/function\s+\w+/.test(line)) {
      inFunction = true;
      currentFunctionLines = 0;
    }
    if (inFunction) {
      currentFunctionLines++;
      if (line.includes('}') && currentFunctionLines > 50) {
        warnings.push({
          type: 'warning',
          title: 'تابع طولانی',
          description: 'توابع با بیش از ۵۰ خط. پیشنهاد: شکستن به توابع کوچکتر',
          category: 'code_quality',
          confidence: 0.6,
          tags: ['long-function', 'refactoring', 'readability']
        });
        inFunction = false;
      }
    }
  }
  
  // Callback Hell
  if (/\)\s*=>\s*{[\s\S]*\)\s*=>\s*{[\s\S]*\)\s*=>\s*{/i.test(code)) {
    warnings.push({
      type: 'warning',
      title: 'Callback Hell',
      description: 'تو در تویی بیش از حد callback. پیشنهاد: استفاده از async/await',
      category: 'code_quality',
      confidence: 0.8,
      tags: ['callback-hell', 'async', 'refactoring']
    });
  }
  
  return warnings;
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 4: USER TRAINING SYSTEM
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0 Phase 3: ثبت آموزش کاربر
 */
function recordUserTraining(trainingData) {
  try {
    const { type, title, description, content, category, tags, context } = trainingData;
    
    // ایجاد آیتم دانش از آموزش کاربر
    const knowledgeItem = {
      type: type || 'rule',
      title: title,
      description: description,
      content: content,
      category: category || 'code_quality',
      tags: tags || [],
      source: KNOWLEDGE_BASE_CONFIG.KNOWLEDGE_SOURCES.USER_TRAINING,
      confidence: 1.0, // آموزش کاربر اعتماد بالا
      context: context || {}
    };
    
    const result = addKnowledgeItem(knowledgeItem);
    
    if (result.success) {
      Logger.log(`📚 آموزش کاربر ثبت شد: ${title}`);
    }
    
    return result;
    
  } catch (error) {
    Logger.log('❌ خطا در ثبت آموزش: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * ✅ v17.0 Phase 3: ثبت راه‌حل مشکل
 */
function recordErrorSolution(errorData, solutionData) {
  try {
    const knowledgeItem = {
      type: 'solution',
      title: `راه‌حل: ${errorData.errorType || 'خطا'}`,
      description: errorData.errorMessage || '',
      content: solutionData.solution,
      category: errorData.category || 'code_quality',
      tags: [
        'error-solution',
        errorData.errorType,
        ...(solutionData.tags || [])
      ].filter(Boolean),
      source: KNOWLEDGE_BASE_CONFIG.KNOWLEDGE_SOURCES.ERROR_RESOLUTION,
      conditions: [
        { type: 'error_pattern', pattern: errorData.errorPattern || errorData.errorMessage }
      ],
      examples: [{
        error: errorData,
        solution: solutionData.solution,
        result: solutionData.result || 'success'
      }]
    };
    
    return addKnowledgeItem(knowledgeItem);
    
  } catch (error) {
    Logger.log('❌ خطا در ثبت راه‌حل: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * ✅ v17.0 Phase 3: ثبت قالب کد
 */
function recordCodeTemplate(templateData) {
  try {
    const knowledgeItem = {
      type: 'template',
      title: templateData.name,
      description: templateData.description || '',
      content: templateData.code,
      category: templateData.category || 'code_quality',
      tags: ['template', 'snippet', ...(templateData.tags || [])],
      language: templateData.language,
      platform: templateData.platform,
      source: KNOWLEDGE_BASE_CONFIG.KNOWLEDGE_SOURCES.USER_TRAINING,
      context: {
        useCase: templateData.useCase,
        parameters: templateData.parameters || []
      }
    };
    
    return addKnowledgeItem(knowledgeItem);
    
  } catch (error) {
    Logger.log('❌ خطا در ثبت قالب: ' + error);
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 5: SMART SUGGESTIONS ENGINE
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0 Phase 3: پیشنهادات هوشمند بر اساس کد
 */
function getSmartSuggestions(code, context = {}) {
  try {
    const suggestions = [];
    const language = context.language || detectLanguage(code);
    const platform = context.platform;
    
    // استخراج الگوها از کد فعلی
    const patterns = extractPatternsFromCode(code, language);
    
    // جستجوی دانش مرتبط
    const relevantKnowledge = searchKnowledge('', {
      language: language,
      platform: platform,
      limit: 50
    });
    
    // پیشنهادات بر اساس الگوهای شناسایی شده
    for (const pattern of patterns) {
      if (pattern.type === 'warning') {
        suggestions.push({
          type: 'warning',
          title: pattern.title,
          description: pattern.description,
          confidence: pattern.confidence,
          category: pattern.category,
          source: 'pattern_detection'
        });
      }
    }
    
    // پیشنهادات بر اساس دانش موجود
    if (relevantKnowledge.success && relevantKnowledge.results.length > 0) {
      for (const item of relevantKnowledge.results.slice(0, 5)) {
        if (item.type === 'best_practice' || item.type === 'rule') {
          // بررسی آیا این قاعده در کد رعایت نشده
          if (shouldSuggestItem(item, code)) {
            suggestions.push({
              type: 'suggestion',
              title: item.title,
              description: item.description,
              content: item.content,
              confidence: item.confidence * item.score,
              category: item.category,
              source: 'knowledge_base',
              itemId: item.id
            });
          }
        }
      }
    }
    
    // پیشنهادات بر اساس خطاهای مشابه
    const errorSolutions = findRelevantSolutions(code);
    suggestions.push(...errorSolutions);
    
    // مرتب‌سازی بر اساس اعتماد
    suggestions.sort((a, b) => b.confidence - a.confidence);
    
    return {
      success: true,
      suggestions: suggestions.slice(0, 10),
      patterns: patterns.filter(p => p.type !== 'warning')
    };
    
  } catch (error) {
    Logger.log('❌ خطا در دریافت پیشنهادات: ' + error);
    return { success: false, error: error.message, suggestions: [] };
  }
}

/**
 * ✅ v17.0 Phase 3: تشخیص زبان
 */
function detectLanguage(code) {
  if (/function\s+\w+\s*\(/.test(code) && !/def\s+\w+/.test(code)) {
    return 'javascript';
  }
  if (/def\s+\w+\s*\(|import\s+\w+|from\s+\w+\s+import/.test(code)) {
    return 'python';
  }
  if (/public\s+class|private\s+void|extends\s+\w+/.test(code)) {
    return 'java';
  }
  if (/<html|<div|<script/.test(code)) {
    return 'html';
  }
  return 'unknown';
}

/**
 * ✅ v17.0 Phase 3: بررسی نیاز به پیشنهاد
 */
function shouldSuggestItem(item, code) {
  // اگر شرایط تعریف شده، بررسی کن
  if (item.conditions && item.conditions.length > 0) {
    for (const condition of item.conditions) {
      if (condition.type === 'missing_pattern') {
        const regex = new RegExp(condition.pattern, 'i');
        if (!regex.test(code)) {
          return true; // الگو وجود ندارد، پیشنهاد بده
        }
      }
    }
    return false;
  }
  
  // بدون شرایط خاص، پیشنهاد نده
  return false;
}

/**
 * ✅ v17.0 Phase 3: یافتن راه‌حل‌های مرتبط
 */
function findRelevantSolutions(code) {
  const solutions = [];
  const kb = getOrCreateKnowledgeBase();
  
  const solutionItems = kb.items.filter(item => item.type === 'solution');
  
  for (const item of solutionItems) {
    if (item.conditions) {
      for (const condition of item.conditions) {
        if (condition.type === 'error_pattern') {
          const regex = new RegExp(condition.pattern, 'i');
          if (regex.test(code)) {
            solutions.push({
              type: 'solution',
              title: item.title,
              description: item.description,
              content: item.content,
              confidence: item.confidence * item.score,
              category: item.category,
              source: 'error_solution',
              itemId: item.id
            });
          }
        }
      }
    }
  }
  
  return solutions;
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 6: BENCHMARK & PROGRESS TRACKING
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0 Phase 3: تنظیمات معیارها
 */
const BENCHMARK_CONFIG = {
  METRICS: {
    CODE_QUALITY: {
      id: 'code_quality',
      label: 'کیفیت کد',
      icon: '✨',
      factors: ['documentation', 'error_handling', 'naming', 'structure']
    },
    SECURITY: {
      id: 'security',
      label: 'امنیت',
      icon: '🔒',
      factors: ['input_validation', 'auth', 'encryption', 'no_hardcoded']
    },
    PERFORMANCE: {
      id: 'performance',
      label: 'عملکرد',
      icon: '⚡',
      factors: ['caching', 'optimization', 'async', 'lazy_loading']
    },
    MAINTAINABILITY: {
      id: 'maintainability',
      label: 'قابلیت نگهداری',
      icon: '🔧',
      factors: ['modularity', 'separation', 'testing', 'documentation']
    }
  }
};

/**
 * ✅ v17.0 Phase 3: ارزیابی کد بر اساس معیارها
 */
function evaluateCodeAgainstBenchmarks(code, language) {
  const evaluation = {
    overall: 0,
    metrics: {},
    suggestions: [],
    timestamp: new Date().toISOString()
  };
  
  // ارزیابی کیفیت کد
  evaluation.metrics.code_quality = evaluateCodeQuality(code, language);
  
  // ارزیابی امنیت
  evaluation.metrics.security = evaluateSecurity(code);
  
  // ارزیابی عملکرد
  evaluation.metrics.performance = evaluatePerformance(code);
  
  // ارزیابی قابلیت نگهداری
  evaluation.metrics.maintainability = evaluateMaintainability(code);
  
  // محاسبه امتیاز کلی
  const scores = Object.values(evaluation.metrics);
  evaluation.overall = scores.reduce((sum, m) => sum + m.score, 0) / scores.length;
  
  // تولید پیشنهادات بهبود
  for (const [key, metric] of Object.entries(evaluation.metrics)) {
    if (metric.score < 70) {
      evaluation.suggestions.push({
        category: key,
        message: `امتیاز ${BENCHMARK_CONFIG.METRICS[key.toUpperCase()]?.label} پایین است (${metric.score}%)`,
        improvements: metric.improvements || []
      });
    }
  }
  
  return evaluation;
}

/**
 * ✅ v17.0 Phase 3: ارزیابی کیفیت کد
 */
function evaluateCodeQuality(code, language) {
  let score = 100;
  const improvements = [];
  
  // بررسی مستندات
  const hasJSDoc = /\/\*\*[\s\S]*?\*\//.test(code);
  const hasComments = /\/\/.*|\/\*[\s\S]*?\*\//.test(code);
  if (!hasJSDoc && !hasComments) {
    score -= 15;
    improvements.push('اضافه کردن مستندات و کامنت');
  }
  
  // بررسی نام‌گذاری
  const hasGoodNaming = /function\s+[a-z][a-zA-Z]+/.test(code);
  if (!hasGoodNaming) {
    score -= 10;
    improvements.push('استفاده از نام‌گذاری camelCase');
  }
  
  // بررسی خطای console.log
  const consoleCount = (code.match(/console\.log/g) || []).length;
  if (consoleCount > 5) {
    score -= 10;
    improvements.push('حذف console.log های اضافی');
  }
  
  // بررسی ساختار
  const hasModules = /export|import|module\.exports|require\(/.test(code);
  if (code.length > 2000 && !hasModules) {
    score -= 10;
    improvements.push('استفاده از ماژول‌ها برای سازماندهی');
  }
  
  return { score: Math.max(0, score), improvements };
}

/**
 * ✅ v17.0 Phase 3: ارزیابی امنیت
 */
function evaluateSecurity(code) {
  let score = 100;
  const improvements = [];
  
  // بررسی اطلاعات حساس
  if (/password\s*=\s*['"][^'"]+['"]|api[_-]?key\s*=\s*['"][^'"]+['"]/i.test(code)) {
    score -= 30;
    improvements.push('حذف اطلاعات حساس از کد');
  }
  
  // بررسی اعتبارسنجی ورودی
  const hasInputHandling = /req\.(body|params|query)|input|form/i.test(code);
  const hasValidation = /validate|sanitize|escape/i.test(code);
  if (hasInputHandling && !hasValidation) {
    score -= 20;
    improvements.push('اضافه کردن اعتبارسنجی ورودی');
  }
  
  // بررسی SQL Injection
  if (/query\s*\(\s*['"`].*\$\{/.test(code) || /query\s*\(\s*['"`].*\+/.test(code)) {
    score -= 25;
    improvements.push('استفاده از پارامترهای prepared');
  }
  
  // بررسی eval
  if (/eval\s*\(/.test(code)) {
    score -= 20;
    improvements.push('جایگزینی eval با روش‌های امن‌تر');
  }
  
  return { score: Math.max(0, score), improvements };
}

/**
 * ✅ v17.0 Phase 3: ارزیابی عملکرد
 */
function evaluatePerformance(code) {
  let score = 100;
  const improvements = [];
  
  // بررسی async/await
  const hasAsyncOperations = /fetch|http|database|query|file/i.test(code);
  const hasAsync = /async\s+function|await\s+/.test(code);
  if (hasAsyncOperations && !hasAsync) {
    score -= 15;
    improvements.push('استفاده از async/await برای عملیات غیرهمزمان');
  }
  
  // بررسی حلقه‌های ناکارآمد
  if (/for\s*\([^)]+\)\s*{[\s\S]*?for\s*\([^)]+\)\s*{[\s\S]*?for\s*\(/i.test(code)) {
    score -= 20;
    improvements.push('بازنگری حلقه‌های تو در تو');
  }
  
  // بررسی کش
  const hasDatabase = /database|query|fetch/i.test(code);
  const hasCache = /cache|memoize|memo/i.test(code);
  if (hasDatabase && !hasCache) {
    score -= 10;
    improvements.push('پیاده‌سازی کش برای بهبود عملکرد');
  }
  
  return { score: Math.max(0, score), improvements };
}

/**
 * ✅ v17.0 Phase 3: ارزیابی قابلیت نگهداری
 */
function evaluateMaintainability(code) {
  let score = 100;
  const improvements = [];
  
  const lines = code.split('\n');
  const functionCount = (code.match(/function\s+\w+/g) || []).length;
  
  // بررسی اندازه فایل
  if (lines.length > 500) {
    score -= 15;
    improvements.push('تقسیم فایل به فایل‌های کوچکتر');
  }
  
  // بررسی تعداد توابع
  if (functionCount > 20) {
    score -= 10;
    improvements.push('گروه‌بندی توابع در ماژول‌های جداگانه');
  }
  
  // بررسی جداسازی نگرانی‌ها
  const hasMixedConcerns = /innerHTML|style\.|className/.test(code) && /fetch|http|database/.test(code);
  if (hasMixedConcerns) {
    score -= 15;
    improvements.push('جداسازی منطق UI از منطق داده');
  }
  
  // بررسی تست
  const hasTests = /test\(|describe\(|it\(|expect\(/i.test(code);
  if (!hasTests && functionCount > 5) {
    score -= 10;
    improvements.push('اضافه کردن تست‌های واحد');
  }
  
  return { score: Math.max(0, score), improvements };
}

/**
 * ✅ v17.0 Phase 3: ذخیره تاریخچه ارزیابی
 */
function saveEvaluationHistory(projectId, evaluation) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context) return { success: false, error: 'پروژه یافت نشد' };
    
    if (!context.evaluationHistory) {
      context.evaluationHistory = [];
    }
    
    context.evaluationHistory.push({
      ...evaluation,
      id: `eval_${Date.now()}`
    });
    
    // نگهداری فقط ۵۰ ارزیابی آخر
    if (context.evaluationHistory.length > 50) {
      context.evaluationHistory = context.evaluationHistory.slice(-50);
    }
    
    saveSmartProjectContext(projectId, context);
    
    return { success: true };
    
  } catch (error) {
    Logger.log('❌ خطا در ذخیره ارزیابی: ' + error);
    return { success: false, error: error.message };
  }
}

/**
 * ✅ v17.0 Phase 3: دریافت روند پیشرفت
 */
function getProgressTrend(projectId) {
  try {
    const context = loadSmartProjectContext(projectId);
    if (!context || !context.evaluationHistory) {
      return { success: true, trend: [], message: 'تاریخچه‌ای موجود نیست' };
    }
    
    const history = context.evaluationHistory;
    const trend = history.map(eval => ({
      date: eval.timestamp,
      overall: eval.overall,
      codeQuality: eval.metrics?.code_quality?.score || 0,
      security: eval.metrics?.security?.score || 0,
      performance: eval.metrics?.performance?.score || 0,
      maintainability: eval.metrics?.maintainability?.score || 0
    }));
    
    // محاسبه تغییر
    let change = 0;
    if (trend.length >= 2) {
      const last = trend[trend.length - 1];
      const prev = trend[trend.length - 2];
      change = last.overall - prev.overall;
    }
    
    return {
      success: true,
      trend,
      currentScore: trend[trend.length - 1]?.overall || 0,
      change,
      evaluationCount: trend.length
    };
    
  } catch (error) {
    Logger.log('❌ خطا در دریافت روند: ' + error);
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 7: ADAPTIVE INTERFACE SYSTEM
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0 Phase 3: تنظیمات رابط تطبیقی
 */
const ADAPTIVE_UI_CONFIG = {
  PROJECT_TYPES: {
    WEB_APP: {
      fields: ['frontend_framework', 'backend_framework', 'database', 'hosting'],
      sections: ['api_design', 'ui_components', 'authentication'],
      templates: ['crud_api', 'auth_flow', 'data_model']
    },
    MOBILE_APP: {
      fields: ['platform', 'framework', 'backend', 'push_notifications'],
      sections: ['screens', 'navigation', 'offline_support'],
      templates: ['screen_template', 'api_service', 'local_storage']
    },
    API_SERVICE: {
      fields: ['api_type', 'authentication', 'rate_limiting', 'documentation'],
      sections: ['endpoints', 'models', 'middleware'],
      templates: ['endpoint', 'middleware', 'validator']
    },
    DATA_PIPELINE: {
      fields: ['data_sources', 'processing', 'storage', 'scheduling'],
      sections: ['extractors', 'transformers', 'loaders'],
      templates: ['etl_job', 'data_model', 'scheduler']
    },
    AUTOMATION: {
      fields: ['triggers', 'actions', 'integrations', 'scheduling'],
      sections: ['workflows', 'connectors', 'monitoring'],
      templates: ['workflow', 'connector', 'alert']
    }
  }
};

/**
 * ✅ v17.0 Phase 3: دریافت تنظیمات رابط بر اساس نوع پروژه
 */
function getAdaptiveUIConfig(projectType) {
  const config = ADAPTIVE_UI_CONFIG.PROJECT_TYPES[projectType?.toUpperCase()];
  
  if (!config) {
    // تنظیمات پیش‌فرض
    return {
      fields: ['name', 'description', 'technology', 'status'],
      sections: ['overview', 'tasks', 'files'],
      templates: []
    };
  }
  
  return config;
}

/**
 * ✅ v17.0 Phase 3: تولید فیلدهای داینامیک
 */
function generateDynamicFields(projectType, existingData = {}) {
  const config = getAdaptiveUIConfig(projectType);
  const fields = [];
  
  const fieldDefinitions = {
    // Web App Fields
    frontend_framework: { label: 'فریم‌ورک فرانت‌اند', type: 'select', options: ['React', 'Vue', 'Angular', 'Svelte', 'Vanilla JS'] },
    backend_framework: { label: 'فریم‌ورک بک‌اند', type: 'select', options: ['Node.js', 'Python/Flask', 'Python/Django', 'PHP', 'Java/Spring', 'Go'] },
    database: { label: 'دیتابیس', type: 'select', options: ['PostgreSQL', 'MySQL', 'MongoDB', 'Firebase', 'SQLite'] },
    hosting: { label: 'میزبانی', type: 'select', options: ['Vercel', 'Netlify', 'AWS', 'GCP', 'Azure', 'DigitalOcean'] },
    
    // Mobile App Fields
    platform: { label: 'پلتفرم', type: 'multiselect', options: ['iOS', 'Android', 'Web'] },
    framework: { label: 'فریم‌ورک', type: 'select', options: ['React Native', 'Flutter', 'Swift', 'Kotlin', 'Ionic'] },
    push_notifications: { label: 'نوتیفیکیشن', type: 'checkbox' },
    
    // API Fields
    api_type: { label: 'نوع API', type: 'select', options: ['REST', 'GraphQL', 'gRPC', 'WebSocket'] },
    authentication: { label: 'احراز هویت', type: 'select', options: ['JWT', 'OAuth2', 'API Key', 'Session'] },
    rate_limiting: { label: 'محدودیت نرخ', type: 'checkbox' },
    documentation: { label: 'مستندات', type: 'select', options: ['Swagger', 'Postman', 'Custom'] },
    
    // Data Pipeline Fields
    data_sources: { label: 'منابع داده', type: 'multiselect', options: ['Database', 'API', 'File', 'Stream'] },
    processing: { label: 'پردازش', type: 'select', options: ['Batch', 'Stream', 'Real-time'] },
    storage: { label: 'ذخیره‌سازی', type: 'select', options: ['Data Warehouse', 'Data Lake', 'Database'] },
    scheduling: { label: 'زمان‌بندی', type: 'select', options: ['Cron', 'Event-based', 'Manual'] },
    
    // Automation Fields
    triggers: { label: 'محرک‌ها', type: 'multiselect', options: ['Schedule', 'Webhook', 'Email', 'Form'] },
    actions: { label: 'اقدامات', type: 'multiselect', options: ['Email', 'Notification', 'API Call', 'File'] },
    integrations: { label: 'یکپارچه‌سازی', type: 'multiselect', options: ['Slack', 'Teams', 'Jira', 'GitHub'] }
  };
  
  for (const fieldId of config.fields) {
    const def = fieldDefinitions[fieldId];
    if (def) {
      fields.push({
        id: fieldId,
        ...def,
        value: existingData[fieldId] || null
      });
    }
  }
  
  return fields;
}

/**
 * ✅ v17.0 Phase 3: دریافت قالب‌های پیشنهادی
 */
function getSuggestedTemplates(projectType, context = {}) {
  const kb = getOrCreateKnowledgeBase();
  const templates = [];
  
  // قالب‌های از پایگاه دانش
  const kbTemplates = kb.items.filter(item => 
    item.type === 'template' &&
    (!item.platform || item.platform === projectType)
  );
  
  templates.push(...kbTemplates.map(t => ({
    id: t.id,
    name: t.title,
    description: t.description,
    code: t.content,
    category: t.category,
    source: 'knowledge_base'
  })));
  
  // قالب‌های پیش‌فرض
  const defaultTemplates = getDefaultTemplates(projectType);
  templates.push(...defaultTemplates);
  
  return templates;
}

/**
 * ✅ v17.0 Phase 3: قالب‌های پیش‌فرض
 */
function getDefaultTemplates(projectType) {
  const templates = {
    WEB_APP: [
      {
        id: 'api_endpoint',
        name: 'API Endpoint',
        description: 'قالب پایه برای endpoint',
        code: `function handleRequest(req, res) {
  try {
    // Validate input
    const data = validateInput(req.body);
    
    // Process
    const result = processData(data);
    
    // Return response
    return res.json({ success: true, data: result });
  } catch (error) {
    return res.status(500).json({ success: false, error: error.message });
  }
}`,
        category: 'api'
      }
    ],
    API_SERVICE: [
      {
        id: 'middleware',
        name: 'Middleware',
        description: 'قالب middleware',
        code: `function authMiddleware(req, res, next) {
  const token = req.headers.authorization;
  
  if (!token) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  
  try {
    const decoded = verifyToken(token);
    req.user = decoded;
    next();
  } catch (error) {
    return res.status(403).json({ error: 'Invalid token' });
  }
}`,
        category: 'security'
      }
    ]
  };
  
  return templates[projectType] || [];
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 SECTION 8: API ENDPOINTS FOR PHASE 3
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ✅ v17.0 Phase 3: API - جستجوی دانش
 */
function apiSearchKnowledge(query, filters) {
  return searchKnowledge(query, filters);
}

/**
 * ✅ v17.0 Phase 3: API - اضافه کردن دانش
 */
function apiAddKnowledge(itemData) {
  return addKnowledgeItem(itemData);
}

/**
 * ✅ v17.0 Phase 3: API - ثبت آموزش
 */
function apiRecordTraining(trainingData) {
  return recordUserTraining(trainingData);
}

/**
 * ✅ v17.0 Phase 3: API - ثبت راه‌حل خطا
 */
function apiRecordSolution(errorData, solutionData) {
  return recordErrorSolution(errorData, solutionData);
}

/**
 * ✅ v17.0 Phase 3: API - ثبت قالب
 */
function apiRecordTemplate(templateData) {
  return recordCodeTemplate(templateData);
}

/**
 * ✅ v17.0 Phase 3: API - پیشنهادات هوشمند
 */
function apiGetSmartSuggestions(code, context) {
  return getSmartSuggestions(code, context);
}

/**
 * ✅ v17.0 Phase 3: API - استخراج الگوها
 */
function apiExtractPatterns(code, language) {
  return {
    success: true,
    patterns: extractPatternsFromCode(code, language)
  };
}

/**
 * ✅ v17.0 Phase 3: API - ارزیابی کد
 */
function apiEvaluateCode(projectId, code, language) {
  const evaluation = evaluateCodeAgainstBenchmarks(code, language);
  
  if (projectId) {
    saveEvaluationHistory(projectId, evaluation);
  }
  
  return { success: true, evaluation };
}

/**
 * ✅ v17.0 Phase 3: API - روند پیشرفت
 */
function apiGetProgressTrend(projectId) {
  return getProgressTrend(projectId);
}

/**
 * ✅ v17.0 Phase 3: API - امتیازدهی دانش
 */
function apiUpdateKnowledgeScore(itemId, action) {
  return updateKnowledgeScore(itemId, action);
}

/**
 * ✅ v17.0 Phase 3: API - تنظیمات رابط تطبیقی
 */
function apiGetAdaptiveUI(projectType, existingData) {
  return {
    success: true,
    config: getAdaptiveUIConfig(projectType),
    fields: generateDynamicFields(projectType, existingData),
    templates: getSuggestedTemplates(projectType)
  };
}

/**
 * ✅ v17.0 Phase 3: API - آمار پایگاه دانش
 */
function apiGetKnowledgeStats() {
  try {
    const kb = getOrCreateKnowledgeBase();
    
    const stats = {
      totalItems: kb.items.length,
      byType: {},
      byCategory: {},
      topUsed: [],
      recentlyAdded: [],
      totalUsage: kb.statistics.totalUsage || 0
    };
    
    // شمارش بر اساس نوع
    for (const item of kb.items) {
      stats.byType[item.type] = (stats.byType[item.type] || 0) + 1;
      stats.byCategory[item.category] = (stats.byCategory[item.category] || 0) + 1;
    }
    
    // پرکاربردترین
    stats.topUsed = [...kb.items]
      .sort((a, b) => b.usageCount - a.usageCount)
      .slice(0, 5)
      .map(item => ({ id: item.id, title: item.title, usageCount: item.usageCount }));
    
    // جدیدترین
    stats.recentlyAdded = [...kb.items]
      .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
      .slice(0, 5)
      .map(item => ({ id: item.id, title: item.title, createdAt: item.createdAt }));
    
    return { success: true, stats };
    
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 END OF PHASE 3 - INCREMENTAL LEARNING SYSTEM
// ═══════════════════════════════════════════════════════════════════════════════
