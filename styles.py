def build_stylesheet(t: dict) -> str:
    accent    = t["accent"]
    accent2   = t["accent2"]
    bg        = t["bg"]
    bg2       = t.get("bg2", bg)
    bg3       = t.get("bg3", bg2)
    sidebar   = t["sidebar"]
    text      = t["text"]
    text2     = t.get("text2", text)
    dim       = t["dim"]
    border    = t["border"]
    chat_bg   = t["chat_bg"]
    term_bg   = t["term_bg"]
    term_text = t["term_text"]
    success   = t.get("success", accent)
    warning   = t.get("warning", "#f59e0b")
    error     = t.get("error", "#ef4444")
    user_msg  = t.get("user_msg", bg3)
    ai_msg    = t.get("ai_msg", bg2)
    chat_page     = t.get("chat_page", bg)
    terminal_page = t.get("terminal_page", bg)
    timeline_page = t.get("timeline_page", bg)
    warnings_page = t.get("warnings_page", bg)
    selfmod_page  = t.get("selfmod_page", bg)
    patterns_page = t.get("patterns_page", bg)

    return f"""
    QWidget {{
        background: {bg};
        color: {text};
        font-family: 'Segoe UI', 'Inter', sans-serif;
        font-size: 10pt;
    }}

    QMainWindow {{ background: {bg}; }}

    /* ── Title Bar ─────────────────────────────────────────────── */
    #TitleBar {{
        background: {sidebar};
        border-bottom: 1px solid {border};
    }}
    #TitleLogo {{
        color: {accent};
        background: transparent;
        font-size: 16px;
        font-weight: 700;
    }}
    #TitleLabel {{
        color: {text};
        font-size: 12pt;
        font-weight: 600;
        letter-spacing: 4px;
        background: transparent;
    }}
    #TitleSubtitle {{
        color: {dim};
        font-size: 8.5pt;
        font-weight: 400;
        background: transparent;
    }}
    #TitleBtn {{
        background: transparent;
        color: {dim};
        border: none;
        font-size: 12pt;
        padding: 0;
    }}
    #TitleBtn:hover {{
        background: rgba(255,255,255,0.08);
        color: {text};
    }}
    #TitleBtnClose {{
        background: transparent;
        color: {dim};
        border: none;
        font-size: 12pt;
        padding: 0;
    }}
    #TitleBtnClose:hover {{
        background: rgba(239,68,68,0.2);
        color: {error};
    }}
    #TitleBtnSettings {{
        background: transparent;
        color: {dim};
        border: none;
        font-size: 14pt;
        padding: 0;
    }}
    #TitleBtnSettings:hover {{
        background: rgba(255,255,255,0.08);
        color: {accent};
    }}

    /* ── Sidebar Rail ──────────────────────────────────────────── */
    #Sidebar {{
        background: {sidebar};
        border-right: 1px solid {border};
    }}
    #RailLogo {{
        color: {accent};
        font-size: 22px;
        font-weight: 800;
        background: transparent;
    }}
    #RailBtn {{
        background: transparent;
        color: {dim};
        border: none;
        border-radius: 14px;
        font-size: 18px;
        padding: 0;
    }}
    #RailBtn:hover {{
        background: rgba(255,255,255,0.06);
        color: {text2};
    }}
    #RailBtnActive {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}25, stop:1 {accent}08);
        color: {accent};
        border: 1px solid {accent}35;
        border-radius: 14px;
        font-size: 18px;
        padding: 0;
    }}
    #RailStatIcon {{
        background: transparent;
        color: {dim};
        font-size: 9px;
    }}
    #RailStatBar {{
        background: rgba(255,255,255,0.05);
        border-radius: 2px;
    }}
    #RailStatFill {{
        background: {accent};
        border-radius: 2px;
    }}

    /* ── Glass Panels ──────────────────────────────────────────── */
    #GlassPanel {{
        background: {bg2};
        border: 1px solid {border};
        border-radius: 18px;
    }}
    #GlassPanelHeader {{
        background: transparent;
        border-bottom: 1px solid {border};
        border-radius: 18px 18px 0 0;
    }}
    #GlassPanelTitle {{
        color: {text2};
        font-size: 8pt;
        font-weight: 700;
        letter-spacing: 3px;
        font-family: 'Consolas', 'SF Mono', monospace;
        background: transparent;
    }}
    #GlassPanelDot {{
        color: {accent};
        background: transparent;
        font-size: 7px;
    }}

    /* ── Page Backgrounds ──────────────────────────────────────────── */
    #ChatPage     {{ background: {chat_page}; }}
    #TerminalPage {{ background: {terminal_page}; }}
    #TimelinePage {{ background: {timeline_page}; }}
    #WarningsPage {{ background: {warnings_page}; }}
    #SelfModPage  {{ background: {selfmod_page}; }}
    #PatternsPage {{ background: {patterns_page}; }}

    /* ── Quick Action Buttons ──────────────────────────────────── */
    #QuickBtn {{
        background: {bg3};
        color: {text2};
        border: 1px solid {border};
        border-radius: 14px;
        font-size: 10pt;
        padding: 10px 6px;
        text-align: center;
    }}
    #QuickBtn:hover {{
        background: {accent}14;
        color: {text};
        border-color: {accent}40;
    }}
    #QuickBtn:pressed {{
        background: {accent}0a;
        border-color: {accent}60;
    }}

    /* ── Chat Area ─────────────────────────────────────────────── */
    #ChatArea {{
        background: transparent;
        border: none;
    }}
    #MessageRole {{
        color: {dim};
        font-size: 7.5pt;
        font-weight: 600;
        letter-spacing: 1px;
        text-transform: uppercase;
        padding: 0 2px 4px 2px;
        background: transparent;
    }}
    #AiBubble {{
        background: {ai_msg};
        color: {text};
        border: 1px solid {border};
        border-radius: 16px;
        border-top-left-radius: 4px;
        padding: 14px 18px;
        font-size: 10pt;
        line-height: 1.7;
    }}
    #UserBubble {{
        background: {user_msg};
        color: {text};
        border: 1px solid {accent}30;
        border-radius: 16px;
        border-top-right-radius: 4px;
        padding: 14px 18px;
        font-size: 10pt;
        line-height: 1.7;
    }}
    #TypingIndicator {{
        color: {dim};
        font-size: 8.5pt;
        font-style: italic;
        padding: 6px 16px;
        background: transparent;
    }}
    #STTStatus {{
        color: {accent};
        font-size: 8pt;
        padding: 4px 16px;
        background: transparent;
    }}
    #SuggestionBtn {{
        background: transparent;
        color: {dim};
        border: 1px solid {border};
        border-radius: 20px;
        padding: 6px 14px;
        font-size: 8pt;
    }}
    #SuggestionBtn:hover {{
        background: {accent}12;
        color: {accent};
        border-color: {accent}45;
    }}
    #ChatInput {{
        background: {bg2};
        color: {text};
        border: 1px solid {border};
        border-radius: 14px;
        padding: 12px 16px;
        font-size: 10pt;
        selection-background-color: {accent}40;
    }}
    #ChatInput:focus {{
        border-color: {accent}55;
    }}
    #ChatInput::placeholder {{
        color: {dim};
    }}
    #SendBtn {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 {accent2});
        color: #0a0a0a;
        border: none;
        border-radius: 14px;
        padding: 10px 0;
        font-weight: 700;
        font-size: 10pt;
    }}
    #SendBtn:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent2}, stop:1 {accent});
    }}
    #SendBtn:pressed {{
        background: {accent};
    }}

    /* ── Input Area Container ──────────────────────────────────── */
    #InputArea {{
        background: transparent;
    }}
    #SuggestionsRow {{
        background: transparent;
    }}

    /* ── Status Bar ────────────────────────────────────────────── */
    #StatusBar {{
        background: {sidebar};
        border-top: 1px solid {border};
    }}
    #StatusDot {{
        color: {success};
        background: transparent;
        font-size: 8px;
    }}
    #StatusDotOffline {{
        color: {error};
        background: transparent;
        font-size: 8px;
    }}
    #StatusLabel {{
        color: {dim};
        font-size: 8pt;
        background: transparent;
    }}
    #LLMLabel {{
        color: {dim};
        font-size: 7.5pt;
        font-family: 'Consolas', monospace;
        background: transparent;
    }}

    /* ── Terminal ──────────────────────────────────────────────── */
    #TerminalOutput {{
        background: {term_bg};
        color: {term_text};
        border: 1px solid {border};
        border-radius: 16px;
        padding: 18px;
        font-size: 9pt;
        font-family: 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace;
        selection-background-color: {accent}30;
    }}
    #TerminalInput {{
        background: {bg2};
        color: {term_text};
        border: 1px solid {border};
        border-radius: 12px;
        padding: 10px 14px;
        font-size: 10pt;
        font-family: 'Cascadia Code', 'Consolas', monospace;
        selection-background-color: {accent}30;
    }}
    #TerminalInput:focus {{
        border-color: {accent}50;
    }}
    #TerminalPrompt {{
        color: {accent};
        font-family: 'Cascadia Code', monospace;
        font-size: 12pt;
        font-weight: 700;
        background: transparent;
    }}

    /* ── Section Headers ───────────────────────────────────────── */
    #SectionHeader {{
        color: {text};
        font-size: 14pt;
        font-weight: 600;
        background: transparent;
    }}

    /* ── Timeline ──────────────────────────────────────────────── */
    #TimelineEntry {{
        background: {bg2};
        border: 1px solid {border};
        border-left: 3px solid {accent};
        border-radius: 10px;
        margin: 3px 0;
    }}
    #TimelineTime {{
        color: {dim};
        font-size: 8pt;
        font-family: 'Consolas', monospace;
        background: transparent;
    }}
    #TimelineText {{
        color: {text};
        font-size: 9pt;
        background: transparent;
    }}

    /* ── Warnings ──────────────────────────────────────────────── */
    #WarningEntryError {{
        background: rgba(239,68,68,0.06);
        border: 1px solid rgba(239,68,68,0.2);
        border-left: 3px solid {error};
        border-radius: 10px;
        margin: 3px 0;
    }}
    #WarningEntryWarning {{
        background: rgba(245,158,11,0.06);
        border: 1px solid rgba(245,158,11,0.2);
        border-left: 3px solid {warning};
        border-radius: 10px;
        margin: 3px 0;
    }}
    #WarningEntryInfo {{
        background: {bg2};
        border: 1px solid {border};
        border-left: 3px solid {accent};
        border-radius: 10px;
        margin: 3px 0;
    }}
    #ClearWarningsBtn {{
        background: {bg3};
        color: {dim};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 7px 16px;
    }}
    #ClearWarningsBtn:hover {{
        color: {text};
        border-color: {accent}40;
    }}

    /* ── Self-Mod ──────────────────────────────────────────────── */
    #ProposalCard {{
        background: {bg2};
        border: 1px solid {border};
        border-radius: 16px;
        margin: 5px 0;
    }}
    #ProposalTitle {{
        color: {text};
        font-size: 10pt;
        font-weight: 600;
        background: transparent;
    }}
    #ProposalText {{
        color: {text2};
        font-size: 9pt;
        background: transparent;
    }}
    #ProposalMeta {{
        color: {dim};
        font-size: 8pt;
        background: transparent;
    }}
    #ApproveBtn {{
        background: {accent}18;
        color: {accent};
        border: 1px solid {accent}45;
        border-radius: 10px;
        padding: 8px 20px;
        font-weight: 600;
    }}
    #ApproveBtn:hover {{
        background: {accent}28;
    }}
    #RejectBtn {{
        background: rgba(239,68,68,0.08);
        color: {error};
        border: 1px solid rgba(239,68,68,0.25);
        border-radius: 10px;
        padding: 8px 20px;
    }}
    #RejectBtn:hover {{
        background: rgba(239,68,68,0.15);
    }}
    #RollbackBtn {{
        background: {bg3};
        color: {dim};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 5px 12px;
    }}
    #RollbackBtn:hover {{
        color: {text};
        border-color: {accent}40;
    }}
    #LedgerEntry {{
        background: {bg2};
        border: 1px solid {border};
        border-radius: 10px;
        margin: 3px 0;
    }}
    #LedgerEntryRolledBack {{
        background: transparent;
        border: 1px dashed {border};
        border-radius: 10px;
        margin: 3px 0;
    }}
    #AnalyzeBtn {{
        background: {accent}18;
        color: {accent};
        border: 1px solid {accent}45;
        border-radius: 10px;
        padding: 8px 20px;
        font-weight: 600;
    }}
    #AnalyzeBtn:hover {{
        background: {accent}28;
    }}

    /* ── Patterns Page ─────────────────────────────────────────── */
    #PatternBrowser {{
        background: {bg2};
        border-right: 1px solid {border};
    }}
    #PatternSearch {{
        background: {bg3};
        color: {text};
        border: 1px solid {border};
        border-radius: 12px;
        padding: 9px 14px;
        selection-background-color: {accent}30;
    }}
    #PatternSearch:focus {{
        border-color: {accent}55;
    }}
    #PatternCount {{
        color: {dim};
        font-size: 8pt;
        font-family: 'Consolas', monospace;
        background: transparent;
    }}
    #PatternCard {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 12px;
    }}
    #PatternCard:hover {{
        background: {bg3};
        border-color: {border};
    }}
    #PatternCardActive {{
        background: {accent}10;
        border: 1px solid {accent}40;
        border-radius: 12px;
    }}
    #PatternCardName {{
        color: {text};
        font-size: 9.5pt;
        font-weight: 600;
        background: transparent;
    }}
    #PatternCardSlug {{
        color: {accent};
        font-size: 8pt;
        font-family: 'Consolas', monospace;
        background: transparent;
    }}
    #PatternCardPreview {{
        color: {dim};
        font-size: 8pt;
        background: transparent;
    }}
    #PatternInput {{
        background: {bg3};
        color: {text};
        border: 1px solid {border};
        border-radius: 12px;
        padding: 11px 14px;
        selection-background-color: {accent}30;
    }}
    #PatternInput:focus {{
        border-color: {accent}55;
    }}
    #PatternRunBtn {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 {accent2});
        color: #0a0a0a;
        border: none;
        border-radius: 12px;
        padding: 10px 0;
        font-weight: 700;
    }}
    #PatternRunBtn:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent2}, stop:1 {accent});
    }}
    #PatternRunBtn:disabled {{
        background: {bg3};
        color: {dim};
    }}
    #PatternOutput {{
        background: {bg2};
        color: {text};
        border: 1px solid {border};
        border-radius: 14px;
        padding: 16px 18px;
        line-height: 1.7;
    }}
    #PatternStatus {{
        color: {dim};
        font-size: 8pt;
        font-family: 'Consolas', monospace;
        background: transparent;
    }}
    #PatternActionBtn {{
        background: {bg3};
        color: {dim};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 6px 14px;
    }}
    #PatternActionBtn:hover {{
        color: {text};
        border-color: {accent}45;
    }}
    #PatternToggleBtn {{
        background: transparent;
        color: {dim};
        border: none;
        text-align: left;
        font-size: 8pt;
        padding: 2px 0;
    }}
    #PatternToggleBtn:hover {{
        color: {text};
    }}
    #PatternPromptPreview {{
        background: {bg2};
        color: {dim};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 10px;
        font-family: 'Consolas', monospace;
        font-size: 8pt;
    }}

    /* ── Tabs ──────────────────────────────────────────────────── */
    QTabWidget::pane {{
        border: 1px solid {border};
        border-radius: 14px;
        background: {bg2};
    }}
    QTabBar::tab {{
        background: transparent;
        color: {dim};
        border: none;
        padding: 9px 20px;
        border-radius: 10px;
        margin: 3px;
    }}
    QTabBar::tab:selected {{
        background: {accent}15;
        color: {accent};
        font-weight: 600;
    }}
    QTabBar::tab:hover {{
        background: rgba(255,255,255,0.04);
        color: {text};
    }}

    /* ── Generic Buttons ───────────────────────────────────────── */
    QPushButton {{
        background: {bg3};
        color: {text2};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 7px 16px;
    }}
    QPushButton:hover {{
        background: rgba(255,255,255,0.06);
        color: {text};
        border-color: {accent}40;
    }}
    QPushButton:pressed {{
        background: rgba(255,255,255,0.03);
    }}

    /* ── Scroll Bars ───────────────────────────────────────────── */
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        border: none;
        margin: 4px 0;
    }}
    QScrollBar::handle:vertical {{
        background: {border};
        border-radius: 3px;
        min-height: 40px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {accent}45;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        height: 0;
    }}

    /* ── Separators ────────────────────────────────────────────── */
    QFrame[frameShape="4"], QFrame[frameShape="5"] {{
        color: {border};
        background: {border};
    }}

    /* ── Tooltips ──────────────────────────────────────────────── */
    QToolTip {{
        background: {bg2};
        color: {text};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 6px 12px;
        font-size: 8.5pt;
    }}
    """