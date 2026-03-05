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
        QMainWindow, QWidget {{ background: {bg}; color: {text}; }}

        #sidebar {{ background: {sidebar}; border-right: 1px solid {border}; }}
        #logoFrame {{ background: {sidebar}; }}
        #logoLabel {{ color: {accent}; letter-spacing: 3px; }}
        #divider {{ background: {border}; }}

        #navBtn {{
            background: transparent; color: {dim}; border: none;
            border-left: 3px solid transparent; border-radius: 0px;
            padding: 0 0 0 18px; text-align: left;
            font-size: 10pt; letter-spacing: 1px;
        }}
        #navBtn:hover {{ background: {bg}; color: {text}; }}
        #navBtn:checked {{
            background: {chat_bg}; color: {accent};
            border-left: 3px solid {accent};
        }}

        #sysLabel {{ color: {dim}; padding: 0 10px 0 16px; line-height: 1.6; }}
        #healthLabel {{ color: {accent2}; letter-spacing: 1px; }}

        #sysListWidget {{
            background: {sidebar}; color: {dim}; border: none;
            font-size: 8pt; font-family: Consolas;
            outline: 0;
        }}
        #sysListWidget::item {{
            padding: 2px 16px;
            border: none;
        }}
        #sysListWidget::item:hover {{
            background: {chat_bg}; color: {accent};
        }}

        #voiceBtn {{
            background: {sidebar}; color: {dim}; border: none;
            border-top: 1px solid {border}; border-radius: 0;
            padding: 0 20px; text-align: left; letter-spacing: 1px;
        }}
        #voiceBtn:hover {{ background: {chat_bg}; color: {accent}; }}

        #themeBtn {{
            background: {bg}; color: {dim}; border: 1px solid {border};
            border-radius: 3px; font-size: 7pt; letter-spacing: 0.5px;
        }}
        #themeBtn:hover {{ background: {chat_bg}; color: {accent}; }}

        #mainArea {{ background: {bg}; }}
        #topBar {{ background: {bg}; border-bottom: 1px solid {border}; }}
        #pageTitle {{ color: {text}; letter-spacing: 2px; }}
        #statusDot {{ color: {accent}; letter-spacing: 1px; }}
        #confidenceLabel {{ color: {dim}; letter-spacing: 1px; }}

        #modeBtn {{
            background: {chat_bg}; color: {dim}; border: 1px solid {border};
            border-radius: 3px; padding: 2px 8px; letter-spacing: 0.5px;
        }}
        #modeBtn:hover {{ color: {accent}; border-color: {accent}; }}

        #accentLine {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {accent}, stop:0.4 {accent2}, stop:1 transparent);
        }}

        #chatDisplay {{
            background: {chat_bg}; color: {text}; border: 1px solid {border};
            border-radius: 4px; padding: 16px;
            selection-background-color: {accent}30;
        }}

        #collapsibleSection {{ background: transparent; }}
        #collapseToggle {{
            background: {chat_bg}; color: {dim}; border: 1px solid {border};
            border-radius: 4px; padding: 6px 12px; text-align: left;
            letter-spacing: 1px; font-size: 9pt;
        }}
        #collapseToggle:hover {{ background: {bg}; color: {accent}; border-color: {accent}40; }}
        #collapseContent {{
            background: {bg}; border: 1px solid {border};
            border-top: none; border-radius: 0 0 4px 4px;
        }}

        #actionBtn {{
            background: {chat_bg}; color: {dim}; border: 1px solid {border};
            border-radius: 3px; padding: 6px 8px; font-size: 8pt;
            letter-spacing: 0.5px;
        }}
        #actionBtn:hover {{ background: {bg}; color: {accent}; border-color: {accent}50; }}
        #actionBtn:pressed {{ background: {bg}; }}

        #suggestionList {{
            background: {chat_bg}; color: {text}; border: 1px solid {border};
            border-radius: 4px; font-size: 9pt;
        }}
        #suggestionList::item:hover {{ background: {accent}20; }}
        #suggestionList::item:selected {{ background: {accent}40; }}

        #inputContainer {{
            background: {chat_bg}; border: 1px solid {accent}30;
            border-radius: 6px;
        }}
        #inputField {{
            background: transparent; color: {text}; border: none;
            font-size: 10pt; letter-spacing: 0.5px; padding: 4px 0;
        }}
        #inputField::placeholder {{ color: {dim}; }}

        #sendBtn {{
            background: {accent2}; color: #000; border: none; border-radius: 4px;
            padding: 8px 0; font-weight: 700; letter-spacing: 1px;
        }}
        #sendBtn:hover {{ background: {accent}; }}
        #sendBtn:pressed {{ background: {accent2}; }}

        #terminalDisplay {{
            background: {term_bg}; color: {term_text}; border: 1px solid {border};
            border-radius: 4px; padding: 14px; font-size: 9pt;
            selection-background-color: {accent}20;
        }}
        #terminalInput {{
            background: {chat_bg}; color: {term_text}; border: 1px solid {border};
            border-radius: 4px; padding: 8px 12px; font-size: 10pt;
        }}
        #terminalInput:focus {{ border-color: {accent2}60; }}
        #termRunBtn {{
            background: {accent2}; color: #000; border: none; border-radius: 4px;
            padding: 8px 0; font-weight: 700; letter-spacing: 1px;
        }}
        #termRunBtn:hover {{ background: {accent}; }}
        #termClearBtn, #quickBtn {{
            background: {chat_bg}; color: {dim}; border: 1px solid {border};
            border-radius: 4px; padding: 6px 10px; letter-spacing: 0.5px;
        }}
        #termClearBtn:hover, #quickBtn:hover {{
            background: {bg}; color: {accent}; border-color: {accent}40;
        }}

        QScrollBar:vertical {{ background: {bg}; width: 6px; border: none; }}
        QScrollBar::handle:vertical {{
            background: {border}; border-radius: 3px; min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {accent2}40; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar:horizontal {{ height: 0px; }}
    """
