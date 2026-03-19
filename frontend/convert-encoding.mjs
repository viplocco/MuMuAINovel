import { readFile, writeFile } from 'fs/promises';
import iconv from 'iconv-lite';

const files = [
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
];

async function convertFile(filePath) {
  try {
    const buffer = await readFile(filePath);
    
    // Check if file already UTF-8 encoded
    if (buffer.length >= 3 && buffer[0] === 0xEF && buffer[1] === 0xBB && buffer[2] === 0xBF) {
      console.log(`✓ Already UTF-8: ${filePath}`);
      return true;
    }
    
    // Try to decode as GBK
    let content;
    try {
      content = iconv.decode(buffer, 'gbk');
    } catch (error) {
      console.error(`Failed to decode ${filePath} as GBK:`, error.message);
      return false;
    }
    
    // Write back as UTF-8 with BOM
    await writeFile(filePath, '\uFEFF' + content, 'utf8');
    console.log(`✓ Converted: ${filePath}`);
    return true;
  } catch (error) {
    console.error(`✗ Error processing ${filePath}:`, error.message);
    return false;
  }
}

async function main() {
  console.log('Starting encoding conversion...');
  const results = await Promise.all(files.map(file => convertFile(file)));
  const successCount = results.filter(Boolean).length;
  console.log(`\nConversion complete! ${successCount}/${files.length} files converted successfully.`);
}

main().catch(console.error);