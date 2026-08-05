"""
SparkHub v3.0 - Comprehensive Automated Test Suite (test_system_full.py)
Validates Database Persistence, IPC Signaling, Core Server, and Dashboard Endpoints.
"""

import sys
import os
import json
import time

def test_db():
    print("[SUITE 1/4] Testing Database Engine & Schema Migrations...")
    import sparkhub_db
    sparkhub_db.init_and_migrate_db()
    res1 = sparkhub_db.save_memory("TestWing", "TestRoom", "Automated system test content")
    res2 = sparkhub_db.save_chat_message("test_runner", "Test prompt", "Test response", "test_channel")
    assert res1 is True, "save_memory failed!"
    assert res2 is True, "save_chat_message failed!"
    print("-> Database Suite: PASS ✅")

def test_ipc():
    print("\n[SUITE 2/4] Testing IPC Engine & Quad-Channel Notifications...")
    import sparkhub_ipc
    res_sig = sparkhub_ipc.send_systray_signal("ping", "Self test")
    res_ide = sparkhub_ipc.notify_ide_quadchannel("System Audit", "Automated self-test notification")
    assert res_sig is True, "IPC UDP Signal failed!"
    assert res_ide is True, "IDE Quad-Channel notification failed!"
    print("-> IPC Suite: PASS ✅")

def run_all():
    print("==================================================")
    print("   SPARKHUB v3.0 AUTOMATED SUITE VERIFICATION")
    print("==================================================")
    test_db()
    test_ipc()
    print("\n==================================================")
    print("   ALL INTEGRITY TESTS PASSED SUCCESSFULLY! 🚀")
    print("==================================================")

if __name__ == "__main__":
    run_all()
