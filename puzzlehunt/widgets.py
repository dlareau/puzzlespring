from django import forms


class AceEditorWidget(forms.Textarea):
    template_name = 'components/_ace_editor_widget.html'

    class Media:
        js = (
            'ace-src-noconflict/ace.js',
            'ace-src-noconflict/mode-html.js',
            'ace-src-noconflict/theme-chrome.js',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs['class'] = 'ace-editor'
