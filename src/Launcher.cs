using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;
using Microsoft.Win32;

namespace DovahScribeLauncher
{
    static class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            string scriptPath = Path.Combine(baseDir, "app.py");

            if (!File.Exists(scriptPath))
            {
                MessageBox.Show(
                    "Не найден файл ядра 'app.py' в директории приложения:\n" + baseDir,
                    "DovahScribe — Ошибка запуска",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
                return;
            }

            string pythonExe = FindPython(baseDir);

            if (string.IsNullOrEmpty(pythonExe))
            {
                MessageBox.Show(
                    "Интерпретатор Python (pythonw.exe / python.exe / pyw.exe) не найден!\n\n" +
                    "Пожалуйста, убедитесь, что Python установлен или лежит в Runtimes.",
                    "DovahScribe — Ошибка окружения",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Warning
                );
                return;
            }

            // Формируем аргументы запуска
            string scriptArgs = "\"" + scriptPath + "\"";
            if (args != null && args.Length > 0)
            {
                for (int i = 0; i < args.Length; i++)
                {
                    if (args[i].Contains(" "))
                        scriptArgs += " \"" + args[i] + "\"";
                    else
                        scriptArgs += " " + args[i];
                }
            }

            ProcessStartInfo psi = new ProcessStartInfo
            {
                FileName = pythonExe,
                Arguments = scriptArgs,
                WorkingDirectory = baseDir,
                UseShellExecute = false,
                CreateNoWindow = true,
                WindowStyle = ProcessWindowStyle.Hidden
            };

            // Передаем кодировку UTF-8 в дочерний процесс
            psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
            psi.EnvironmentVariables["PYTHONUTF8"] = "1";

            try
            {
                Process.Start(psi);
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "Ошибка при запуске процесса DovahScribe:\n\n" + ex.Message,
                    "DovahScribe — Ошибка",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }
        }

        static string FindPython(string baseDir)
        {
            // 1. Проверяем локальный .venv в текущей папке
            string localVenvPythonw = Path.Combine(baseDir, ".venv", "Scripts", "pythonw.exe");
            if (File.Exists(localVenvPythonw)) return localVenvPythonw;

            string localVenvPython = Path.Combine(baseDir, ".venv", "Scripts", "python.exe");
            if (File.Exists(localVenvPython)) return localVenvPython;

            // 2. Проверяем родительский / соседний Runtimes каталог (Lain_Ai/Runtimes/Python313)
            string[] relativeRuntimes = new string[]
            {
                Path.Combine(baseDir, "..", "Runtimes", "Python313", "pythonw.exe"),
                Path.Combine(baseDir, "..", "Runtimes", "Python313", "python.exe"),
                Path.Combine(baseDir, "..", "Runtimes", "Python312", "pythonw.exe"),
                Path.Combine(baseDir, "..", "Runtimes", "Python312", "python.exe"),
                Path.Combine(baseDir, "..", "Runtimes", "Python311", "pythonw.exe"),
                Path.Combine(baseDir, "..", "Runtimes", "Python311", "python.exe"),
                Path.Combine(baseDir, "..", ".venv", "Scripts", "pythonw.exe"),
                Path.Combine(baseDir, "..", ".venv", "Scripts", "python.exe")
            };

            foreach (string rel in relativeRuntimes)
            {
                try
                {
                    string fullPath = Path.GetFullPath(rel);
                    if (File.Exists(fullPath)) return fullPath;
                }
                catch { }
            }

            // 3. Проверяем Windows Registry (Официальные установленные версии Python)
            string registryPython = FindPythonFromRegistry();
            if (!string.IsNullOrEmpty(registryPython)) return registryPython;

            // 4. Проверяем Python Launcher (pyw.exe / py.exe)
            string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string pywLauncher = Path.Combine(localAppData, "Programs", "Python", "Launcher", "pyw.exe");
            if (File.Exists(pywLauncher)) return pywLauncher;

            string pyLauncher = Path.Combine(localAppData, "Programs", "Python", "Launcher", "py.exe");
            if (File.Exists(pyLauncher)) return pyLauncher;

            // 5. Проверяем PATH
            string pathEnv = Environment.GetEnvironmentVariable("PATH") ?? "";
            string[] paths = pathEnv.Split(Path.PathSeparator);

            foreach (string p in paths)
            {
                if (string.IsNullOrEmpty(p.Trim())) continue;
                try
                {
                    string candidateW = Path.Combine(p.Trim(), "pythonw.exe");
                    if (File.Exists(candidateW)) return candidateW;
                }
                catch { }
            }

            foreach (string p in paths)
            {
                if (string.IsNullOrEmpty(p.Trim())) continue;
                try
                {
                    string candidate = Path.Combine(p.Trim(), "python.exe");
                    if (File.Exists(candidate)) return candidate;
                }
                catch { }
            }

            // 6. Проверяем стандартные пути установки в AppData и C:\
            string[] commonLocations = new string[]
            {
                Path.Combine(localAppData, "Programs", "Python", "Python313", "pythonw.exe"),
                Path.Combine(localAppData, "Programs", "Python", "Python312", "pythonw.exe"),
                Path.Combine(localAppData, "Programs", "Python", "Python311", "pythonw.exe"),
                Path.Combine(localAppData, "Programs", "Python", "Python313", "python.exe"),
                Path.Combine(localAppData, "Programs", "Python", "Python312", "python.exe"),
                Path.Combine(localAppData, "Programs", "Python", "Python311", "python.exe"),
                @"C:\Python313\pythonw.exe",
                @"C:\Python312\pythonw.exe",
                @"C:\Python311\pythonw.exe"
            };


            foreach (string loc in commonLocations)
            {
                if (File.Exists(loc)) return loc;
            }

            return null;
        }

        static string FindPythonFromRegistry()
        {
            string[] subKeys = new string[]
            {
                @"Software\Python\PythonCore",
                @"Software\Wow6432Node\Python\PythonCore"
            };

            RegistryKey[] baseKeys = new RegistryKey[] { Registry.CurrentUser, Registry.LocalMachine };

            foreach (RegistryKey baseKey in baseKeys)
            {
                foreach (string subKey in subKeys)
                {
                    try
                    {
                        using (RegistryKey root = baseKey.OpenSubKey(subKey))
                        {
                            if (root == null) continue;

                            string[] versions = root.GetSubKeyNames();
                            Array.Sort(versions);
                            Array.Reverse(versions); // Новые версии первыми (3.13, 3.12, 3.11...)

                            foreach (string ver in versions)
                            {
                                using (RegistryKey installKey = root.OpenSubKey(ver + @"\InstallPath"))
                                {
                                    if (installKey == null) continue;

                                    object val = installKey.GetValue("") ?? installKey.GetValue("ExecutablePath");
                                    if (val != null)
                                    {
                                        string dir = val.ToString().TrimEnd('\\');
                                        string pw = Path.Combine(dir, "pythonw.exe");
                                        if (File.Exists(pw)) return pw;

                                        string p = Path.Combine(dir, "python.exe");
                                        if (File.Exists(p)) return p;
                                    }
                                }
                            }
                        }
                    }
                    catch { }
                }
            }

            return null;
        }
    }
}
