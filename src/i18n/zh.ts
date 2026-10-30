const zh = {
  // Header
  "app.title": "出行决策助手",
  "app.subtitle": "查附近商场 · 核对品牌门店 · 按距离推荐",

  // Empty state
  "empty.title": "出行决策助手",
  "empty.hint": "告诉我你在哪、想逛哪些品牌，我会用高德地图搜附近商场、核对门店、算好距离再给你推荐。",
  "empty.features": "高德地图 · 门店核对 · 距离排序",

  // Chat input
  "chat.placeholder": "发消息…  ⏎ 发送 · Shift+⏎ 换行",
  "chat.hint": "由 OpenAI Agents SDK + EdgeOne Makers 驱动 · 仅供演示",

  // Preset questions
  "preset.1": "我在红莲南路地铁站附近，想要一个既有倍轻松又有西町村屋的近商场。",
  "preset.2": "我在西单附近，想找一家同时有星巴克和优衣库的商场。",

  // Tool indicators
  "tool.geocode": "定位解析",
  "tool.malls": "商场检索",
  "tool.stores": "门店核对",
  "tool.distance": "距离计算",

  // Status & errors
  "status.error": "⚠️ 请求失败，请检查后端服务是否启动。",
  "status.stopped": "⏹ *已停止生成*",
  "status.backendError": "⚠️ 后端中断请求失败，服务端可能仍在运行。",

  // Debug panel
  "debug.title": "传输流",
  "debug.events": "事件",
  "debug.clear": "清除",
  "debug.empty": "等待 SSE 事件...",
  "debug.emptyHint": "发送消息后，所有原始后端数据将在此处显示。",

  // Conversation sidebar
  "sidebar.label": "会话列表",
  "sidebar.title": "会话",
  "sidebar.newChat": "新建聊天",
  "sidebar.loading": "正在加载会话...",
  "sidebar.loadMore": "加载更多",
  "sidebar.loadingMore": "加载中...",
  "sidebar.emptyTitle": "暂无会话",
  "sidebar.emptyHint": "点击「新建聊天」开始第一段对话。",
  "sidebar.delete": "删除会话",
  "sidebar.deleteConfirm": "确定要永久删除这个会话吗？此操作不可恢复。",

  // Aria labels (button hover/screen-reader)
  "aria.send": "发送",
  "aria.clearHistory": "清除历史",
  "aria.stopGeneration": "停止生成",

  // Language toggle
  "lang.switch": "English",

  // ─── Floating bottom-right action badges ─────────────────────────────
  "floatingLink.deploy": "一键部署",
  "floatingLink.github": "GitHub",
} as const;

export default zh;
