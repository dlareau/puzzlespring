from django import forms


class AceEditorWidget(forms.Textarea):
    template_name = 'components/_ace_editor_widget.html'

    class Media:
        js = (
            'ace-builds/ace.js',
            'ace-builds/mode-html.js',
            'ace-builds/theme-chrome.js',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs['class'] = 'ace-editor'

class ImageWidget(forms.ClearableFileInput):
    template_name = 'components/_image_widget.html'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs['class'] = 'file-input'

class ToggleSwitchWidget(forms.CheckboxInput):
    template_name = 'components/_toggle_switch_widget.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs['class'] = 'toggle-switch'
