#!/usr/bin/env python3
"""
Setup script for PDF Price Book Parser
"""

import os
import sys
import subprocess
import platform

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 11):
        print("❌ Python 3.11 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version}")
    return True

def install_python_dependencies():
    """Install Python dependencies"""
    print("\n📦 Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Python dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Python dependencies: {e}")
        return False

def check_system_dependencies():
    """Check for system dependencies"""
    print("\n🔍 Checking system dependencies...")
    
    system = platform.system().lower()
    missing_deps = []
    
    # Check Tesseract
    try:
        result = subprocess.run(["tesseract", "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Tesseract OCR found")
        else:
            missing_deps.append("tesseract")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        missing_deps.append("tesseract")
    
    # Check Poppler (pdftoppm)
    try:
        result = subprocess.run(["pdftoppm", "-v"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Poppler utilities found")
        else:
            missing_deps.append("poppler")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        missing_deps.append("poppler")
    
    if missing_deps:
        print(f"⚠️  Missing system dependencies: {', '.join(missing_deps)}")
        print_installation_instructions(system, missing_deps)
        return False
    
    return True

def print_installation_instructions(system, missing_deps):
    """Print installation instructions for missing dependencies"""
    print("\n📋 Installation instructions:")
    
    if system == "linux":
        if "tesseract" in missing_deps or "poppler" in missing_deps:
            print("   Ubuntu/Debian:")
            print("   sudo apt-get update")
            print("   sudo apt-get install tesseract-ocr poppler-utils")
            print("\n   CentOS/RHEL:")
            print("   sudo yum install tesseract poppler-utils")
    
    elif system == "darwin":  # macOS
        if "tesseract" in missing_deps or "poppler" in missing_deps:
            print("   macOS:")
            print("   brew install tesseract poppler")
    
    elif system == "windows":
        print("   Windows:")
        print("   Download and install:")
        print("   - Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki")
        print("   - Poppler: http://blog.alivate.com.au/poppler-windows/")
        print("   Make sure to add them to your PATH environment variable")

def create_directories():
    """Create required directories"""
    print("\n📁 Creating required directories...")
    
    directories = [
        'uploads',
        'exports', 
        'logs',
        'static/css',
        'static/js',
        'templates'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"   ✅ {directory}/")
    
    print("✅ All directories created")

def run_tests():
    """Run integration tests"""
    print("\n🧪 Running integration tests...")
    try:
        result = subprocess.run([sys.executable, "test_integration.py"], 
                              capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print("✅ Integration tests passed")
            return True
        else:
            print(f"❌ Integration tests failed:")
            print(result.stdout)
            print(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("❌ Integration tests timed out")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 PDF Price Book Parser Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install Python dependencies
    if not install_python_dependencies():
        sys.exit(1)
    
    # Check system dependencies
    system_deps_ok = check_system_dependencies()
    
    # Create directories
    create_directories()
    
    # Run tests
    if not run_tests():
        print("\n⚠️  Setup completed with warnings")
        print("   Some tests failed, but the application may still work")
    else:
        print("\n✅ Setup completed successfully!")
    
    print("\n🎯 Next steps:")
    print("   1. Run 'python run.py' to start the application")
    print("   2. Open http://localhost:5000 in your browser")
    print("   3. Upload your first PDF price book")
    
    if not system_deps_ok:
        print("\n⚠️  Note: Install missing system dependencies for full functionality")

if __name__ == '__main__':
    main()
