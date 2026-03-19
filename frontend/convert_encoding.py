import os
import chardet  # type: ignore[import-not-found]

# Files to convert
files_to_convert = [
    'src/pages/Foreshadows.tsx',
    'src/pages/Inspiration.tsx', 
    'src/pages/ProjectDetail.tsx',
    'src/pages/ProjectWizardNew.tsx',
    'src/pages/Settings.tsx',
    'src/pages/Sponsor.tsx',
    'src/components/AIProjectGenerator.tsx',
    'src/components/AnnotatedText.tsx',
    'src/components/ChangelogFloatingButton.tsx',
    'src/components/ChangelogModal.tsx',
    'src/components/ChapterAnalysis.tsx',
    'src/components/ChapterReader.tsx',
    'src/components/ExpansionPlanEditor.tsx',
    'src/components/MemorySidebar.tsx',
    'src/components/PartialRegenerateModal.tsx',
    'src/components/PartialRegenerateToolbar.tsx',
    'src/components/ProtectedRoute.tsx',
    'src/components/SSELoadingOverlay.tsx',
    'src/components/SSEProgressBar.tsx',
    'src/components/SSEProgressModal.tsx',
    'src/components/SpringFestival.css',
    'src/components/SpringFestival.tsx',
    'src/components/ThemeSwitch.tsx',
    'src/components/UserMenu.tsx'
]

def convert_file(filepath):
    """Convert file from GBK to UTF-8"""
    try:
        # Read file as binary
        with open(filepath, 'rb') as f:
            content = f.read()
        
        # Detect encoding
        result = chardet.detect(content)
        print(f"File: {filepath}")
        print(f"Detected: {result['encoding']} ({result['confidence']:.2%})")
        
        # Decode as GBK (code page 936)
        text = content.decode('gbk', errors='replace')
        
        # Write as UTF-8 with BOM
        with open(filepath, 'w', encoding='utf-8-sig') as f:
            f.write(text)
        
        print(f"Converted: {filepath}")
        return True
    except Exception as e:
        print(f"Error converting {filepath}: {e}")
        return False

# Main
if __name__ == '__main__':
    converted = 0
    for file in files_to_convert:
        if os.path.exists(file):
            if convert_file(file):
                converted += 1
    
    print(f"\nTotal converted: {converted}/{len(files_to_convert)} files")
