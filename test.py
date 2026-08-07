import sys, traceback
try:
    import sparkhub_systray
    sparkhub_systray.main()
except Exception:
    traceback.print_exc(file=open('test_fatal.log', 'w'))
