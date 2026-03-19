const fs = require('fs');
const path = require('path');

// List of files to convert
const filesToConvert = [
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

// Function to detect and convert encoding
function convertFile(filePath) {
  try {
    // Read file as binary buffer
    const buffer = fs.readFileSync(filePath);
    
    // Try to decode as GBK first
    let content;
    try {
      // Use iconv-lite for proper GBK decoding
      const iconv = require('iconv-lite');
      content = iconv.decode(buffer, 'gbk');
    } catch (e) {
      // If iconv-lite fails, try with default encoding
      content = buffer.toString('utf8');
    }
    
    // Write back as UTF-8
    fs.writeFileSync(filePath, content, 'utf8');
    console.log(`✓ Converted: ${filePath}`);
  } catch (error) {
    console.error(`✗ Error converting ${filePath}:`, error.message);
  }
}

// Install iconv-lite if not available
try {
  require('iconv-lite');
} catch (e) {
  console.log('Installing iconv-lite...');
  const { execSync } = require('child_process');
  execSync('npm install iconv-lite', { stdio: 'inherit' });
}

// Convert all files
console.log('Starting encoding conversion...');
filesToConvert.forEach(file => {
  if (fs.existsSync(file)) {
    convertFile(file);
  } else {
    console.log(`File not found: ${file}`);
  }
});

console.log('Encoding conversion completed!');