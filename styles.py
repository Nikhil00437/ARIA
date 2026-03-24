def build_stylesheet(t: dict) -> str:
    accent    = t["accent"]
    accent2   = t["accent2"]
    bg        = t["bg"]
    sidebar   = t["sidebar"]
    text      = t["text"]
    dim       = t["dim"]
    border    = t["border"]
    chat_bg   = t["chat_bg"]
    term_bg   = t["term_bg"]
    term_text = t["term_text"]

    return f"""
        /* ── Base ─────────────────────────────────────────────────────────── */
        QMainWindow, QWidget {{
            background: {bg};
            color: {text};
            font-family: 'SF Pro Display', 'Segoe UI', 'Inter', sans-serif;
            font-size: 10pt;
        }}

        /* ── Sidebar ──────────────────────────────────────────────────────── */
        #sidebar {{
            background: {sidebar};
            border-right: 1px solid {border};
        }}
        #logoFrame {{
            background: transparent;
            padding: 10px 0 6px 0;
        }}
        #logoLabel {{
            color: {text};
            font-size: 16pt;
            font-weight: 700;
            letter-spacing: 4px;
            padding-left: 24px;
        }}
        #divider {{
            background: {border};
            margin: 4px 16px;
        }}

        /* Nav buttons */
        #navBtn {{
            background: transparent;
            color: {dim};
            border: none;
            border-radius: 10px;
            margin: 2px 10px;
            padding: 10px 16px;
            text-align: left;
            font-size: 10pt;
            font-weight: 500;
            letter-spacing: 0.3px;
        }}
        #navBtn:hover {{
            background: rgba(255,255,255,0.06);
            color: {text};
        }}
        #navBtn:checked {{
            background: rgba(255,255,255,0.10);
            color: {accent};
            font-weight: 600;
        }}

        /* System info */
        #sysListWidget {{
            background: transparent;
            color: {dim};
            border: none;
            font-size: 8pt;
            font-family: 'SF Mono', 'Consolas', monospace;
        }}
        #sysListWidget::item {{
            padding: 3px 20px;
            border: none;
        }}
        #healthLabel {{
            color: {dim};
            font-size: 8pt;
            padding-left: 20px;
            letter-spacing: 0.5px;
        }}

        /* Voice / mic buttons */
        #voiceBtn {{
            background: transparent;
            color: {dim};
            border: none;
            border-radius: 8px;
            margin: 1px 10px;
            padding: 8px 16px;
            text-align: left;
            font-size: 9pt;
            letter-spacing: 0.3px;
        }}
        #voiceBtn:hover {{ background: rgba(255,255,255,0.05); color: {text}; }}

        #micBtn {{
            background: transparent;
            color: {dim};
            border: none;
            border-radius: 8px;
            margin: 1px 10px;
            padding: 8px 16px;
            text-align: left;
            font-size: 9pt;
            letter-spacing: 0.3px;
        }}
        #micBtn:hover {{ background: rgba(255,255,255,0.05); color: {text}; }}
        #micBtn:checked {{ color: #ff6b6b; }}

        /* Theme buttons */
        #themeBtn {{
            background: rgba(255,255,255,0.05);
            color: {dim};
            border: 1px solid {border};
            border-radius: 6px;
            font-size: 7pt;
            padding: 3px 6px;
        }}
        #themeBtn:hover {{ background: rgba(255,255,255,0.10); color: {text}; }}

        /* ── Top bar ──────────────────────────────────────────────────────── */
        #mainArea {{ background: {bg}; }}
        #topBar {{
            background: {bg};
            border-bottom: 1px solid {border};
            padding: 0 8px;
        }}
        #pageTitle {{
            color: {text};
            font-size: 11pt;
            font-weight: 600;
            letter-spacing: 1px;
        }}
        #statusDot {{
            color: {accent};
            font-size: 8pt;
            letter-spacing: 0.5px;
        }}
        #confidenceLabel {{
            color: {dim};
            font-size: 8pt;
            font-family: 'SF Mono', 'Consolas', monospace;
        }}
        #modeBtn {{
            background: rgba(255,255,255,0.06);
            color: {dim};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 3px 12px;
            font-size: 8pt;
            letter-spacing: 0.5px;
        }}
        #modeBtn:hover {{ color: {accent}; border-color: {accent}60; }}

        #accentLine {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 {accent},
                stop:0.5 {accent2},
                stop:1 transparent
            );
        }}

        /* ── Chat display ─────────────────────────────────────────────────── */
        #chatDisplay {{
            background: {chat_bg};
            color: {text};
            border: 1px solid {border};
            border-radius: 14px;
            padding: 20px 24px;
            line-height: 1.7;
            selection-background-color: {accent}30;
        }}

        /* ── Quick actions (collapsible) ──────────────────────────────────── */
        #NavBtn {{
            background: rgba(255,255,255,0.05);
            color: {dim};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 7px 14px;
            text-align: left;
            font-size: 9pt;
        }}
        #NavBtn:hover {{ background: rgba(255,255,255,0.09); color: {text}; }}

        #actionBtn {{
            background: rgba(255,255,255,0.05);
            color: {dim};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 7px 10px;
            font-size: 8pt;
            letter-spacing: 0.3px;
        }}
        #actionBtn:hover {{
            background: rgba(255,255,255,0.09);
            color: {text};
            border-color: {accent}50;
        }}
        #actionBtn:pressed {{ background: rgba(255,255,255,0.04); }}

        /* ── Suggestions ──────────────────────────────────────────────────── */
        #suggestionList {{
            background: {chat_bg};
            color: {text};
            border: 1px solid {border};
            border-radius: 10px;
            font-size: 9pt;
            padding: 4px;
        }}
        #suggestionList::item {{
            padding: 6px 12px;
            border-radius: 7px;
        }}
        #suggestionList::item:hover {{ background: rgba(255,255,255,0.07); }}
        #suggestionList::item:selected {{ background: {accent}25; color: {accent}; }}

        /* ── Input row ────────────────────────────────────────────────────── */
        #inputContainer {{
            background: {chat_bg};
            border: 1px solid {border};
            border-radius: 14px;
            margin: 4px 0;
        }}
        #inputContainer:focus-within {{
            border-color: {accent}60;
        }}
        #inputField {{
            background: transparent;
            color: {text};
            border: none;
            font-size: 10pt;
            padding: 6px 4px;
            letter-spacing: 0.2px;
        }}
        #inputField::placeholder {{ color: {dim}; }}

        #sendBtn {{
            background: {accent};
            color: #000;
            border: none;
            border-radius: 10px;
            padding: 8px 0;
            font-weight: 700;
            font-size: 9pt;
            letter-spacing: 0.5px;
        }}
        #sendBtn:hover {{ background: {accent2}; }}
        #sendBtn:pressed {{ opacity: 0.8; }}

        /* ── STT label ────────────────────────────────────────────────────── */
        #sttLabel {{
            color: {accent};
            background: transparent;
            padding: 3px 16px;
            font-size: 8pt;
            letter-spacing: 0.8px;
        }}

        /* ── Terminal ─────────────────────────────────────────────────────── */
        #terminalDisplay {{
            background: {term_bg};
            color: {term_text};
            border: 1px solid {border};
            border-radius: 14px;
            padding: 18px 20px;
            font-size: 9pt;
            font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
            selection-background-color: {accent}20;
        }}
        #terminalInput {{
            background: {chat_bg};
            color: {term_text};
            border: 1px solid {border};
            border-radius: 10px;
            padding: 10px 14px;
            font-size: 10pt;
            font-family: 'SF Mono', 'Consolas', monospace;
        }}
        #terminalInput:focus {{ border-color: {accent}50; }}

        #termRunBtn {{
            background: {accent};
            color: #000;
            border: none;
            border-radius: 10px;
            padding: 8px 0;
            font-weight: 700;
            font-size: 9pt;
        }}
        #termRunBtn:hover {{ background: {accent2}; }}

        #termClearBtn, #quickBtn {{
            background: rgba(255,255,255,0.05);
            color: {dim};
            border: 1px solid {border};
            border-radius: 10px;
            padding: 8px 12px;
            font-size: 9pt;
        }}
        #termClearBtn:hover, #quickBtn:hover {{
            background: rgba(255,255,255,0.09);
            color: {text};
            border-color: {accent}40;
        }}

        /* ── Self-Mod page ────────────────────────────────────────────────── */
        #SectionHeader {{
            color: {text};
            font-size: 13pt;
            font-weight: 600;
            letter-spacing: 0.5px;
        }}
        #ProposalCard {{
            background: {chat_bg};
            border: 1px solid {border};
            border-radius: 14px;
            margin: 4px 0;
        }}
        #ProposalTitle {{
            color: {text};
            font-size: 10pt;
            font-weight: 600;
        }}
        #ProposalText {{
            color: {text};
            font-size: 9pt;
            line-height: 1.6;
        }}
        #ProposalMeta {{
            color: {dim};
            font-size: 8pt;
        }}
        #ApproveBtn {{
            background: {accent}20;
            color: {accent};
            border: 1px solid {accent}50;
            border-radius: 8px;
            padding: 6px 16px;
            font-weight: 600;
            font-size: 9pt;
        }}
        #ApproveBtn:hover {{ background: {accent}35; }}
        #RejectBtn {{
            background: rgba(255,100,100,0.08);
            color: #ff6b6b;
            border: 1px solid rgba(255,100,100,0.3);
            border-radius: 8px;
            padding: 6px 16px;
            font-size: 9pt;
        }}
        #RejectBtn:hover {{ background: rgba(255,100,100,0.15); }}
        #RollbackBtn {{
            background: rgba(255,255,255,0.05);
            color: {dim};
            border: 1px solid {border};
            border-radius: 7px;
            padding: 4px 10px;
            font-size: 8pt;
        }}
        #RollbackBtn:hover {{ color: {text}; border-color: {accent}40; }}
        #LedgerEntry {{
            background: rgba(255,255,255,0.03);
            border: 1px solid {border};
            border-radius: 10px;
            margin: 2px 0;
        }}
        #LedgerEntryRolledBack {{
            background: transparent;
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 10px;
            margin: 2px 0;
            opacity: 0.5;
        }}
        #AnalyzeBtn {{
            background: {accent}20;
            color: {accent};
            border: 1px solid {accent}50;
            border-radius: 9px;
            padding: 7px 18px;
            font-weight: 600;
            font-size: 9pt;
        }}
        #AnalyzeBtn:hover {{ background: {accent}35; }}

        /* Status bar */
        #StatusBar {{
            background: {sidebar};
            border-top: 1px solid {border};
        }}
        #StatusDot {{ color: {accent}; }}
        #StatusDotOffline {{ color: #ff6b6b; }}

        /* Tabs */
        QTabWidget::pane {{
            border: 1px solid {border};
            border-radius: 10px;
            background: {chat_bg};
        }}
        QTabBar::tab {{
            background: transparent;
            color: {dim};
            border: none;
            padding: 8px 18px;
            font-size: 9pt;
            border-radius: 8px;
            margin: 2px;
        }}
        QTabBar::tab:selected {{
            background: rgba(255,255,255,0.09);
            color: {text};
            font-weight: 600;
        }}
        QTabBar::tab:hover {{ background: rgba(255,255,255,0.06); color: {text}; }}

        /* ── Scrollbars ───────────────────────────────────────────────────── */
        QScrollBar:vertical {{
            background: transparent;
            width: 5px;
            border: none;
            margin: 4px 0;
        }}
        QScrollBar::handle:vertical {{
            background: {border};
            border-radius: 3px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {accent}50; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar:horizontal {{ height: 0px; }}

        /* ── Tooltip ──────────────────────────────────────────────────────── */
        QToolTip {{
            background: {chat_bg};
            color: {text};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 8pt;
        }}
    """
