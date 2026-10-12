# RevitMCP: This script runs in pyRevit (IronPython). Use Python 2.7 syntax.
#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""Starts/connects the RevitMCP External CPython Server for this specific Revit session."""

import sys
import os
import json
import traceback

print("[LaunchRevitMCP] Initializing session connection...")

try:
    from pyrevit import routes, script, revit, DB
    
    doc = revit.doc
    doc_title = doc.Title if doc else "No Document"
    print("[LaunchRevitMCP] Active Document: {}".format(doc_title))

    # 1. Ensure routes API namespace is initialized and routes are registered
    button_dir = os.path.dirname(os.path.abspath(__file__))
    ext_dir = os.path.abspath(os.path.join(button_dir, "..", "..", ".."))
    lib_dir = os.path.join(ext_dir, 'lib')
    if lib_dir not in sys.path:
        sys.path.insert(0, lib_dir)

    startup_file = os.path.join(ext_dir, "startup.py")
    if os.path.exists(startup_file):
        try:
            startup_globals = dict(globals())
            startup_globals['__file__'] = startup_file
            execfile(startup_file, startup_globals)
            print("[LaunchRevitMCP] Routes registered from startup.py.")
        except Exception as se:
            print("[LaunchRevitMCP] Startup registration note: {}".format(se))

    # 2. Activate pyRevit routes server for THIS Revit instance
    from pyrevit.routes import server as routes_server
    active_server = routes_server.get_active_server()
    if not active_server:
        active_server = routes_server.activate_server()

    session_port = active_server.port if active_server else 48884
    print("[LaunchRevitMCP] Routes server running on PORT: {}".format(session_port))

    # 3. Update mcp_config.json so Antigravity MCP server targets THIS session port
    mcp_config_path = r"C:\Users\hazem.sakr\.gemini\config\mcp_config.json"
    if os.path.exists(mcp_config_path):
        try:
            with open(mcp_config_path, 'r') as fp:
                cfg = json.load(fp)
            srv_cfg = cfg.get("mcpServers", {}).get("RevitMCPServer", {})
            if "env" in srv_cfg:
                srv_cfg["env"]["REVITMCP_TARGET_PORT"] = str(session_port)
                with open(mcp_config_path, 'w') as fp:
                    json.dump(cfg, fp, indent=2)
                print("[LaunchRevitMCP] mcp_config.json updated: REVITMCP_TARGET_PORT = {}".format(session_port))
        except Exception as ce:
            print("[LaunchRevitMCP] Warning updating mcp_config.json: {}".format(ce))

    # 4. Check / Ensure the FilledRegionType "360-DIAGONAL BROWN" (ANSI136, RGB(176,119,0))
    if doc:
        try:
            target_frt_name = "360-DIAGONAL BROWN"
            found_frt = None
            for frt in DB.FilteredElementCollector(doc).OfClass(DB.FilledRegionType):
                p = frt.get_Parameter(DB.BuiltInParameter.ALL_MODEL_TYPE_NAME)
                if p and p.AsString() == target_frt_name:
                    found_frt = frt
                    break
            
            if found_frt:
                pat_name = doc.GetElement(found_frt.ForegroundPatternId).Name if found_frt.ForegroundPatternId.IntegerValue > 0 else "None"
                c = found_frt.ForegroundPatternColor
                print("[LaunchRevitMCP] FilledRegionType '{}' verified: Pattern={}, Color=RGB({},{},{})".format(
                    target_frt_name, pat_name, c.Red, c.Green, c.Blue
                ))
            else:
                # Find ANSI136 pattern
                ansi_pat_id = DB.ElementId.InvalidElementId
                for fpe in DB.FilteredElementCollector(doc).OfClass(DB.FillPatternElement):
                    if "ANSI136" in fpe.Name:
                        ansi_pat_id = fpe.Id
                        break
                
                # Duplicate any existing filled region type
                first_frt = None
                for frt in DB.FilteredElementCollector(doc).OfClass(DB.FilledRegionType):
                    first_frt = frt
                    break
                
                if first_frt and ansi_pat_id != DB.ElementId.InvalidElementId:
                    with revit.Transaction("Create 360-DIAGONAL BROWN FilledRegionType"):
                        new_frt = first_frt.Duplicate(target_frt_name)
                        new_frt.ForegroundPatternId = ansi_pat_id
                        new_frt.ForegroundPatternColor = DB.Color(176, 119, 0)
                        new_frt.IsMasking = False
                    print("[LaunchRevitMCP] Created FilledRegionType '{}' with pattern ANSI136 and RGB(176,119,0)".format(target_frt_name))
        except Exception as fe:
            print("[LaunchRevitMCP] Note checking/creating FilledRegionType: {}".format(fe))

    # 5. Launch the external server explicitly pointing to THIS session port
    from RevitMCP_UI import ui_manager
    ui_manager.start_external_server(target_port=session_port)
    print("[LaunchRevitMCP] SUCCESS: External server started for Session Port {} ({})".format(session_port, doc_title))

except Exception as e:
    print("[LaunchRevitMCP] ERROR: {}".format(e))
    traceback.print_exc()
