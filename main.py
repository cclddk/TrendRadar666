def render_html_content(
    report_data: Dict,
    total_titles: int,
    is_daily_summary: bool = False,
    mode: str = "daily",
    update_info: Optional[Dict] = None,
    raw_data: Optional[Dict] = None,
    id_to_name: Optional[Dict] = None
) -> str:
    """
    渲染 HTML，集成【需求1: 置顶新增】、【需求4: 全局搜索】、【新需求: 随机推荐沉底】
    """
    # 准备搜索数据
    search_list = []
    if raw_data:
        for sid, tdata in raw_data.items():
            sname = id_to_name.get(sid, sid) if id_to_name else sid
            for t, info in tdata.items():
                u = info.get("url") or info.get("mobileUrl") or ""
                search_list.append({"t": t, "u": u, "s": sname})
    search_json = json.dumps(search_list, ensure_ascii=False)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TrendRadar 热点追踪</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <style>
            body {{ font-family: -apple-system, sans-serif; margin: 0; padding: 16px; background: #fafafa; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 2px 16px rgba(0,0,0,0.06); overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .word-group {{ margin-bottom: 30px; }}
            .word-header {{ display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding-bottom: 8px; margin-bottom: 12px; }}
            .word-name {{ font-weight: 600; font-size: 18px; }}
            .news-item {{ display: flex; gap: 10px; margin-bottom: 12px; font-size: 14px; align-items: center; }}
            .news-num {{ min-width: 20px; color: #999; text-align: center; }}
            .news-link {{ color: #2563eb; text-decoration: none; }}
            .new-section {{ margin-bottom: 30px; padding: 15px; background: #fffbeb; border-radius: 8px; border: 1px solid #fcd34d; }}
            .new-title {{ color: #92400e; font-weight: bold; margin-bottom: 10px; }}
            .search-box {{ margin-bottom: 20px; position: relative; }}
            #search-input {{ width: 100%; padding: 10px; border: 2px solid #eee; border-radius: 8px; box-sizing: border-box; font-size: 14px; }}
            #search-results {{ display: none; position: absolute; top: 100%; left: 0; right: 0; background: white; border: 1px solid #eee; border-radius: 8px; max-height: 300px; overflow-y: auto; z-index: 100; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
            .search-item {{ padding: 10px; border-bottom: 1px solid #f5f5f5; font-size: 13px; }}
            .search-item a {{ color: #333; text-decoration: none; display: block; }}
            .search-source {{ font-size: 12px; color: #999; margin-top: 2px; }}
            
            /* 随机推荐分隔样式 */
            .random-divider {{ margin: 40px 0 20px 0; border-top: 2px dashed #eee; text-align: center; position: relative; }}
            .random-divider span {{ background: #fff; padding: 0 15px; color: #999; position: relative; top: -10px; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>TrendRadar 热点分析</h2>
                <div style="font-size:12px; opacity:0.8;">{get_beijing_time().strftime('%Y-%m-%d %H:%M')} · {total_titles} 条资讯</div>
            </div>
            <div class="content">
                <div class="search-box">
                    <input type="text" id="search-input" placeholder="🔍 搜索全网热点...">
                    <div id="search-results"></div>
                </div>

    """

    # 1. 新增热点 (置顶)
    if report_data["new_titles"]:
        html += f"""
                <div class="new-section">
                    <div class="new-title">🆕 本次新增热点 ({report_data['total_new_count']} 条)</div>
        """
        for source in report_data["new_titles"]:
            html += f"""<div style="margin-top:8px; font-weight:600; font-size:13px; color:#b45309;">{source['source_name']}</div>"""
            for idx, item in enumerate(source["titles"], 1):
                u = item.get('url') or item.get('mobile_url')
                link = f"<a href='{u}' target='_blank' style='color:#333;'>{item['title']}</a>" if u else item['title']
                html += f"""<div style="font-size:13px; margin-top:4px; padding-left:10px;">{idx}. {link}</div>"""
        html += "</div>"

    # --- 分离【普通热点】和【随机推荐】 ---
    normal_stats = []
    random_stats = []
    
    if report_data["stats"]:
        for stat in report_data["stats"]:
            if "随机" in stat["word"]:
                random_stats.append(stat)
            else:
                normal_stats.append(stat)

    # 2. 渲染普通热点
    for stat in normal_stats:
        word = html_escape(stat["word"])
        html += f"""
            <div class="word-group">
                <div class="word-header">
                    <div class="word-name">{word}</div>
                    <div style="font-size:12px; color:#666;">{stat['count']} 条</div>
                </div>
        """
        for idx, item in enumerate(stat["titles"], 1):
            u = item.get('url') or item.get('mobile_url')
            title_html = f"<a href='{u}' target='_blank' class='news-link'>{item['title']}</a>" if u else item['title']
            html += f"""
                <div class="news-item">
                    <div class="news-num">{idx}</div>
                    <div style="flex:1;">
                        <span style="color:#999; font-size:12px;">[{item['source_name']}]</span>
                        {title_html}
                    </div>
                </div>
            """
        html += "</div>"
        
    # 3. 渲染随机推荐 (沉底)
    if random_stats:
        html += """
            <div class="random-divider">
                <span>以下为随机推荐内容</span>
            </div>
        """
        for stat in random_stats:
            word = html_escape(stat["word"])
            html += f"""
                <div class="word-group">
                    <div class="word-header">
                        <div class="word-name" style="color:#059669;">{word}</div>
                        <div style="font-size:12px; color:#666;">{stat['count']} 条</div>
                    </div>
            """
            for idx, item in enumerate(stat["titles"], 1):
                u = item.get('url') or item.get('mobile_url')
                title_html = f"<a href='{u}' target='_blank' class='news-link'>{item['title']}</a>" if u else item['title']
                html += f"""
                    <div class="news-item">
                        <div class="news-num">{idx}</div>
                        <div style="flex:1;">
                            <span style="color:#999; font-size:12px;">[{item['source_name']}]</span>
                            {title_html}
                        </div>
                    </div>
                """
            html += "</div>"

    if report_data["failed_ids"]:
         html += f"<div style='color:red; font-size:12px; margin-top:20px; padding:10px; background:#fff1f2; border-radius:8px;'>⚠️ 获取失败: {', '.join(report_data['failed_ids'])}</div>"

    html += f"""
            </div>
            <div style="text-align:center; padding:20px; color:#999; font-size:12px; background:#f8f9fa;">
                Powered by TrendRadar v{VERSION}
            </div>
        </div>
        
        <script>
            const allData = {search_json};
            const input = document.getElementById('search-input');
            const results = document.getElementById('search-results');
            input.addEventListener('input', (e) => {{
                const val = e.target.value.trim().toLowerCase();
                if (!val) {{ results.style.display = 'none'; return; }}
                const filtered = allData.filter(i => i.t.toLowerCase().includes(val)).slice(0, 50);
                if (filtered.length > 0) {{
                    results.innerHTML = filtered.map(i => `
                        <div class="search-item">
                            <a href="${{i.u}}" target="_blank">${{i.t}}</a>
                            <div class="search-source">${{i.s}}</div>
                        </div>
                    `).join('');
                }} else {{ results.innerHTML = '<div style="padding:10px; text-align:center; color:#999;">无结果</div>'; }}
                results.style.display = 'block';
            }});
            document.addEventListener('click', (e) => {{
                if (!e.target.closest('.search-box')) results.style.display = 'none';
            }});
        </script>
    </body>
    </html>
    """
    return html
