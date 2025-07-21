from jnius import autoclass

def on_boot():
    PythonService = autoclass('org.kivy.android.PythonService')
    PythonService.start(
        autoclass('org.renpy.pservice.PService').getService(),
        'service'
    )

if __name__ == '__main__':
    on_boot()
