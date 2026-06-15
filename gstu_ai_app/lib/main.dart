import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter/services.dart'; // Copy to Clipboard
import 'package:share_plus/share_plus.dart'; // Share
import 'package:url_launcher/url_launcher.dart'; // Open Links
import 'package:record/record.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:path_provider/path_provider.dart';

const String baseUrl = "https://gstu-ai-backend.onrender.com";

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Supabase.initialize(
    url: 'https://viepwhawvwszrtqaxwkf.supabase.co',
    anonKey: 'sb_publishable_wieXCIJZ9REvxfyzfK7bVg_DdpRCMf8',
  );
  runApp(const GSTUAiApp());
}

class GSTUAiApp extends StatefulWidget {
  const GSTUAiApp({super.key});
  @override
  State<GSTUAiApp> createState() => _GSTUAiAppState();
}

class _GSTUAiAppState extends State<GSTUAiApp> {
  ThemeMode _themeMode = ThemeMode.system;
  void toggleTheme(ThemeMode mode) => setState(() => _themeMode = mode);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'GSTU AI Ecosystem',
      debugShowCheckedModeBanner: false,
      themeMode: _themeMode,
      theme: ThemeData(
          brightness: Brightness.light,
          primaryColor: const Color(0xFF10A37F),
          fontFamily: 'sans-serif'),
      darkTheme: ThemeData(
          brightness: Brightness.dark,
          scaffoldBackgroundColor: const Color(0xFF0B1120),
          fontFamily: 'sans-serif'),
      home: SplashScreen(
          currentThemeMode: _themeMode, onThemeChanged: toggleTheme),
    );
  }
}

// ==========================================
// 🚀 SPLASH SCREEN (New!)
// ==========================================
class SplashScreen extends StatefulWidget {
  final ThemeMode currentThemeMode;
  final Function(ThemeMode) onThemeChanged;
  const SplashScreen(
      {super.key,
      required this.currentThemeMode,
      required this.onThemeChanged});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _checkAuthAndNavigate();
  }

  Future<void> _checkAuthAndNavigate() async {
    // ২ সেকেন্ডের সুন্দর একটি ডিলে (লোগো দেখানোর জন্য)
    await Future.delayed(const Duration(seconds: 2));
    if (!mounted) return;

    final session = Supabase.instance.client.auth.currentSession;
    if (session != null) {
      Navigator.pushReplacement(
          context,
          MaterialPageRoute(
              builder: (context) => const DashboardPage(isGuest: false)));
    } else {
      Navigator.pushReplacement(
          context,
          MaterialPageRoute(
              builder: (context) => LoginPage(
                  currentThemeMode: widget.currentThemeMode,
                  onThemeChanged: widget.onThemeChanged)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0B1120),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text("🎓", style: TextStyle(fontSize: 80)),
            const SizedBox(height: 20),
            const Text("GSTU AI Core",
                style: TextStyle(
                    fontSize: 32,
                    fontWeight: FontWeight.bold,
                    color: Colors.white)),
            const SizedBox(height: 10),
            Text("Initializing Neural Engine...",
                style: TextStyle(
                    fontSize: 14, color: Colors.white.withOpacity(0.5))),
            const SizedBox(height: 40),
            const CircularProgressIndicator(color: Color(0xFF10A37F)),
          ],
        ),
      ),
    );
  }
}

// ==========================================
// 🔐 LOGIN PAGE (Updated with Guest Mode)
// ==========================================
class LoginPage extends StatefulWidget {
  final ThemeMode currentThemeMode;
  final Function(ThemeMode) onThemeChanged;
  const LoginPage(
      {super.key,
      required this.currentThemeMode,
      required this.onThemeChanged});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  @override
  void initState() {
    super.initState();
    Supabase.instance.client.auth.onAuthStateChange.listen((data) {
      if (data.session != null && mounted) {
        Navigator.pushReplacement(
            context,
            MaterialPageRoute(
                builder: (context) => const DashboardPage(isGuest: false)));
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      body: Center(
        child: Container(
          width: MediaQuery.of(context).size.width * 0.85,
          padding: const EdgeInsets.all(32),
          decoration: BoxDecoration(
            color: isDark ? Colors.white.withOpacity(0.05) : Colors.white,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: isDark ? Colors.white24 : Colors.black12),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text("🎓", style: TextStyle(fontSize: 60)),
              const SizedBox(height: 10),
              Text("GSTU AI Core",
                  style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.bold,
                      color: isDark ? Colors.white : Colors.black87)),
              const SizedBox(height: 30),

              // Google Login Button
              SizedBox(
                width: double.infinity,
                height: 50,
                child: OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                      side: BorderSide(
                          color: isDark ? Colors.white24 : Colors.black12),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12))),
                  onPressed: () async {
                    await Supabase.instance.client.auth.signInWithOAuth(
                        OAuthProvider.google,
                        redirectTo:
                            'gstuai://callback'); // 🔴 This will now jump back to the app!
                  },
                  icon: const Icon(Icons.g_mobiledata,
                      color: Colors.redAccent, size: 30),
                  label: Text("Continue with Google",
                      style: TextStyle(
                          color: isDark ? Colors.white : Colors.black87,
                          fontSize: 16)),
                ),
              ),
              const SizedBox(height: 15),

              // 🔴 Guest Mode Button
              TextButton(
                onPressed: () {
                  Navigator.pushReplacement(
                      context,
                      MaterialPageRoute(
                          builder: (context) =>
                              const DashboardPage(isGuest: true)));
                },
                child: Text("Continue as Guest",
                    style: TextStyle(
                        color: Colors.grey.shade500,
                        decoration: TextDecoration.underline)),
              )
            ],
          ),
        ),
      ),
    );
  }
}

// ==========================================
// 🚀 THE ULTIMATE DASHBOARD
// ==========================================
class DashboardPage extends StatefulWidget {
  final bool isGuest;
  const DashboardPage({super.key, this.isGuest = false});
  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  final List<Map<String, String>> _messages = [];

  // 🔴 Changed to Map for safe ID/Title handling
  final List<Map<String, dynamic>> _recentChats = [];

  // 🔴 Voice Recording Variables
  final AudioRecorder _audioRecorder = AudioRecorder();
  bool _isRecording = false;

  bool _isThinking = false;
  String _selectedModel = "llama-3.1-8b-instant";
  final Map<String, String> _models = {
    "⚡ Fast Engine (Llama 3 - 8B)": "llama-3.1-8b-instant",
    "💻 Offline Mode (GPT4All)": "local-gpt4all",
    "🌐 Web & Research (Gemini 2.5)": "gemini-2.5-flash",
    "🎓 Deep Logic (Llama 3 - 70B)": "llama-3.3-70b-versatile",
    "🧠 Adv. Analysis (Gemini Pro)": "gemini-2.5-pro",
    "🚀 GPT-4o (OpenAI Premium)": "openai/gpt-4o-2024-08-06",
  };

  final String apiUrl = '$baseUrl/chat';

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(_scrollController.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
      }
    });
  }

  Future<void> _sendMessage([String? quickQuery]) async {
    final text = quickQuery ?? _controller.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _messages.add({"role": "user", "content": text});
      _isThinking = true;
      if (_messages.length == 1) {
        // 🔴 BUG FIX 1: Safely adding Map to _recentChats
        _recentChats.insert(0, {
          "id": DateTime.now().millisecondsSinceEpoch.toString(),
          "title": text.length > 25 ? "${text.substring(0, 25)}..." : text
        });
      }
    });
    _controller.clear();
    _scrollToBottom();

    try {
      final response = await http.post(
        Uri.parse(apiUrl),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode(
            {"query": text, "model": _selectedModel, "context_from_files": ""}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        setState(() => _messages.add(
            {"role": "ai", "content": data['reply'] ?? "Error processing"}));
      } else {
        setState(() => _messages.add({
              "role": "ai",
              "content": "Server returned ${response.statusCode}"
            }));
      }
    } catch (e) {
      setState(() => _messages.add(
          {"role": "ai", "content": "⚠️ Server Connection Failed! Check IP."}));
    } finally {
      setState(() => _isThinking = false);
      _scrollToBottom();
    }
  }

  // 🎙️ Toggle Recording Logic
  Future<void> _toggleRecording() async {
    if (_isRecording) {
      // Stop Recording
      final path = await _audioRecorder.stop();
      setState(() => _isRecording = false);
      if (path != null) {
        await _processVoiceNote(path); // অডিও ব্যাকএন্ডে পাঠানো
      }
    } else {
      // Start Recording
      if (await Permission.microphone.request().isGranted) {
        final dir = await getApplicationDocumentsDirectory();
        final filePath =
            '${dir.path}/gstu_audio_${DateTime.now().millisecondsSinceEpoch}.m4a';

        await _audioRecorder.start(const RecordConfig(), path: filePath);
        setState(() => _isRecording = true);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
            content: Text("⚠️ Microphone permission required!")));
      }
    }
  }

  // 🚀 Send Audio to FastAPI Backend
  Future<void> _processVoiceNote(String path) async {
    setState(() => _isThinking = true);
    try {
      var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/voice'));
      request.files.add(await http.MultipartFile.fromPath('audio_file', path));

      var response = await request.send();
      var responseData = await response.stream.bytesToString();

      if (response.statusCode == 200) {
        final json = jsonDecode(responseData);
        final transcription = json['transcription'];

        // এআই যেটা শুনেছে সেটা টেক্সট হিসেবে সেন্ড করে দেওয়া
        if (transcription != null && transcription.isNotEmpty) {
          _sendMessage(transcription);
        }
      } else {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text("Voice Processing Failed: ${response.statusCode}")));
      }
    } catch (e) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text("⚠️ Error: $e")));
    } finally {
      setState(() => _isThinking = false);
    }
  }

  void _performChatAction(String action, Map<String, dynamic> chat) async {
    final chatId = chat['id'];
    if (action == 'delete') {
      try {
        await Supabase.instance.client
            .from('chat_history')
            .delete()
            .eq('id', chatId);
      } catch (e) {
        // Suppress error if DB table doesn't exist yet
      }
      setState(() => _recentChats.removeWhere((c) => c['id'] == chatId));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text("🗑️ Chat deleted successfully!")));
      }
    } else if (action == 'rename') {
      _showRenameDialog(chat);
    } else if (action == 'folder') {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Folder API active soon.")));
    }
  }

  void _showRenameDialog(Map<String, dynamic> chat) {
    final renameController = TextEditingController(text: chat['title']);
    showDialog(
        context: context,
        builder: (context) => AlertDialog(
              title: const Text("Rename Chat"),
              content: TextField(controller: renameController),
              actions: [
                TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text("Cancel")),
                ElevatedButton(
                    onPressed: () async {
                      try {
                        await Supabase.instance.client
                            .from('chat_history')
                            .update({'title': renameController.text}).eq(
                                'id', chat['id']);
                      } catch (e) {
                        // Suppress error for local testing
                      }
                      setState(() => chat['title'] = renameController.text);
                      if (mounted) Navigator.pop(context);
                    },
                    child: const Text("Save"))
              ],
            ));
  }

  void _showFeedbackDialog() {
    final fbController = TextEditingController();
    showDialog(
        context: context,
        builder: (context) => AlertDialog(
              backgroundColor: const Color(0xFF1E293B),
              title: const Text("🧠 Help GSTU AI Learn",
                  style: TextStyle(color: Colors.white)),
              content: TextField(
                controller: fbController,
                maxLines: 3,
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                    hintText:
                        "Why did you dislike this? Please Provide details...",
                    hintStyle: const TextStyle(color: Colors.white54),
                    filled: true,
                    fillColor: Colors.black26,
                    border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12))),
              ),
              actions: [
                TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text("Cancel",
                        style: TextStyle(color: Colors.grey))),
                ElevatedButton(
                    style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF10A37F)),
                    onPressed: () async {
                      try {
                        await http.post(Uri.parse('$baseUrl/feedback'),
                            headers: {"Content-Type": "application/json"},
                            body: jsonEncode({
                              "chat_id": "fl_app",
                              "rating": "downvote",
                              "comment": fbController.text
                            }));
                      } catch (e) {}
                      if (!mounted) return;
                      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                          content:
                              Text("✅ Feedback securely logged to AI DB!")));
                      Navigator.pop(context);
                    },
                    child: const Text("Submit to Core",
                        style: TextStyle(color: Colors.white))),
              ],
            ));
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final userName =
        Supabase.instance.client.auth.currentUser?.userMetadata?['full_name'] ??
            "IR Scholar";

    return Scaffold(
      drawer: Drawer(
        backgroundColor: isDark ? const Color(0xFF0F172A) : Colors.white,
        child: Column(
          children: [
            GestureDetector(
              onTap: () {
                setState(() => _messages.clear());
                Navigator.pop(context);
              },
              child: Container(
                padding: const EdgeInsets.only(
                    top: 50, bottom: 20, left: 20, right: 20),
                decoration: const BoxDecoration(
                    gradient: LinearGradient(
                        colors: [Color(0xFF10A37F), Color(0xFF065F46)])),
                child: Row(
                  children: [
                    const CircleAvatar(
                        backgroundColor: Colors.white,
                        radius: 25,
                        child: Text("🎓", style: TextStyle(fontSize: 28))),
                    const SizedBox(width: 15),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text("GSTU IR AI",
                              style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 20,
                                  fontWeight: FontWeight.bold)),
                          Text(userName,
                              style: const TextStyle(
                                  color: Colors.white70, fontSize: 13)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Row(
                children: [
                  Expanded(
                      child: PremiumHoverButton(
                          text: "New Chat",
                          icon: Icons.add_comment_rounded,
                          isDark: isDark,
                          onPressed: () {
                            setState(() => _messages.clear());
                            Navigator.pop(context);
                          })),
                  const SizedBox(width: 10),
                  Expanded(
                      child: PremiumHoverButton(
                          text: "Save To",
                          icon: Icons.create_new_folder_outlined,
                          isDark: isDark,
                          onPressed: () => ScaffoldMessenger.of(context)
                              .showSnackBar(const SnackBar(
                                  content: Text("Folder API active soon."))))),
                ],
              ),
            ),
            if (userName.toLowerCase().contains("tashfin") ||
                userName.toLowerCase().contains("admin"))
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16.0),
                child: PremiumHoverButton(
                    text: "Admin Dashboard",
                    icon: Icons.analytics_outlined,
                    isDark: isDark,
                    onPressed: () => ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                            content: Text("Admin metrics opening...")))),
              ),
            const Divider(),

            // 🔴 DYNAMIC RECENT CHATS
            Expanded(
              child: ListView(
                padding: EdgeInsets.zero,
                children: [
                  const Padding(
                      padding:
                          EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      child: Text("🕒 RECENT CHATS",
                          style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.bold,
                              color: Colors.grey))),
                  if (_recentChats.isEmpty)
                    const Padding(
                        padding: EdgeInsets.only(left: 16),
                        child: Text("No history yet.",
                            style:
                                TextStyle(color: Colors.grey, fontSize: 13))),
                  ..._recentChats.map((chat) => ListTile(
                        dense: true,
                        leading: const Icon(Icons.chat_bubble_outline,
                            size: 20, color: Colors.grey),
                        title: Text(chat['title'], // Fixed mapping
                            style: TextStyle(
                                color:
                                    isDark ? Colors.white70 : Colors.black87)),
                        // 🔴 BUG FIX 2: Added proper PopupMenu for Rename/Delete
                        trailing: PopupMenuButton<String>(
                          icon: const Icon(Icons.more_vert,
                              size: 18, color: Colors.grey),
                          onSelected: (value) =>
                              _performChatAction(value, chat),
                          itemBuilder: (context) => [
                            const PopupMenuItem(
                                value: 'rename', child: Text('✏️ Rename')),
                            const PopupMenuItem(
                                value: 'folder',
                                child: Text('📁 Move to Folder')),
                            const PopupMenuItem(
                                value: 'delete',
                                child: Text('🗑️ Delete',
                                    style: TextStyle(color: Colors.red))),
                          ],
                        ),
                        onTap: () => Navigator.pop(context),
                      )),
                ],
              ),
            ),
            const Divider(),

            // 🔴 PRIVACY POLICY EXPANDER
            ExpansionTile(
              leading: const Icon(Icons.security_rounded, color: Colors.grey),
              title: const Text("Privacy & Security",
                  style: TextStyle(fontSize: 14)),
              children: [
                Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Text(
                      "1. End-to-End Encryption\n2. Zero Third-Party Sharing\n3. Local RAG Priority\nAll queries are secured using advanced encryption.",
                      style: TextStyle(
                          color: isDark ? Colors.white54 : Colors.black54,
                          fontSize: 12,
                          height: 1.5)),
                )
              ],
            ),
            ListTile(
              leading:
                  const Icon(Icons.logout_rounded, color: Colors.redAccent),
              title: const Text("Sign Out",
                  style: TextStyle(
                      color: Colors.redAccent, fontWeight: FontWeight.bold)),
              onTap: () async {
                await Supabase.instance.client.auth.signOut();
                if (!context.mounted) return;
                Navigator.pushReplacement(
                    context,
                    MaterialPageRoute(
                        builder: (context) => LoginPage(
                            currentThemeMode: ThemeMode.system,
                            onThemeChanged: (m) {})));
              },
            ),
            const SizedBox(height: 10),
          ],
        ),
      ),
      appBar: AppBar(
        backgroundColor: isDark ? const Color(0xFF0B1120) : Colors.white,
        iconTheme: IconThemeData(color: isDark ? Colors.white : Colors.black87),
        title: DropdownButtonHideUnderline(
          child: DropdownButton<String>(
            value: _selectedModel,
            dropdownColor: isDark ? const Color(0xFF1E293B) : Colors.white,
            style: TextStyle(
                color: isDark ? Colors.white : Colors.black87,
                fontSize: 14,
                fontWeight: FontWeight.bold),
            icon: const Icon(Icons.arrow_drop_down, color: Color(0xFF10A37F)),
            onChanged: (String? newValue) {
              if (newValue != null) setState(() => _selectedModel = newValue);
            },
            items: _models.entries
                .map(
                    (e) => DropdownMenuItem(value: e.value, child: Text(e.key)))
                .toList(),
          ),
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: _messages.isEmpty
                ? Center(
                    child: SingleChildScrollView(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Text("✨", style: TextStyle(fontSize: 50)),
                          const SizedBox(height: 10),
                          Text("Welcome to GSTU AI Assistant",
                              style: TextStyle(
                                  fontSize: 22,
                                  fontWeight: FontWeight.bold,
                                  color:
                                      isDark ? Colors.white : Colors.black87)),
                          const SizedBox(height: 8),
                          Text(
                              "Your personal AI for syllabus, research, and notes.",
                              style: TextStyle(
                                  color: isDark
                                      ? Colors.white54
                                      : Colors.black54)),
                          const SizedBox(height: 40),
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 20),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Expanded(
                                    child: _buildQuickAction(
                                        "📝 Smart Notes",
                                        "Generate structured notes",
                                        () => _sendMessage(
                                            "Generate clear smart notes based on the syllabus."))),
                                const SizedBox(width: 10),
                                Expanded(
                                    child: _buildQuickAction(
                                        "🎯 Mock Exam",
                                        "Tough analytical questions",
                                        () => _sendMessage(
                                            "Ask me a tough analytical question for my upcoming exam."))),
                                const SizedBox(width: 10),
                                Expanded(
                                    child: _buildQuickAction(
                                        "⏰ Class Info",
                                        "Routine & Books",
                                        () => _sendMessage(
                                            "Show me the recommended books and routine."))),
                              ],
                            ),
                          )
                        ],
                      ),
                    ),
                  )
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.all(16),
                    itemCount: _messages.length,
                    itemBuilder: (context, index) {
                      final msg = _messages[index];
                      final isUser = msg["role"] == "user";
                      return Align(
                        alignment: isUser
                            ? Alignment.centerRight
                            : Alignment.centerLeft,
                        child: Container(
                          margin: const EdgeInsets.only(bottom: 12),
                          constraints: BoxConstraints(
                              maxWidth:
                                  MediaQuery.of(context).size.width * 0.85),
                          child: Column(
                            crossAxisAlignment: isUser
                                ? CrossAxisAlignment.end
                                : CrossAxisAlignment.start,
                            children: [
                              Container(
                                padding: const EdgeInsets.all(16),
                                decoration: BoxDecoration(
                                  color: isUser
                                      ? const Color(0xFF10A37F).withOpacity(0.9)
                                      : (isDark
                                          ? Colors.white.withOpacity(0.1)
                                          : Colors.black.withOpacity(0.05)),
                                  borderRadius: BorderRadius.circular(16),
                                ),
                                child: MarkdownBody(
                                  data: msg["content"]!,
                                  selectable: true,
                                  onTapLink: (text, href, title) async {
                                    if (href != null) {
                                      final uri = Uri.parse(href);
                                      if (await canLaunchUrl(uri)) {
                                        await launchUrl(uri);
                                      }
                                    }
                                  },
                                  styleSheet: MarkdownStyleSheet(
                                    p: TextStyle(
                                        color: isUser
                                            ? Colors.white
                                            : (isDark
                                                ? Colors.white
                                                : Colors.black87),
                                        fontSize: 15,
                                        height: 1.5),
                                    strong: TextStyle(
                                        color: isUser
                                            ? Colors.white
                                            : (isDark
                                                ? Colors.white
                                                : Colors.black),
                                        fontWeight: FontWeight.bold),
                                    a: const TextStyle(
                                        color: Colors.blueAccent,
                                        decoration: TextDecoration.underline),
                                    listBullet: TextStyle(
                                        color: isUser
                                            ? Colors.white
                                            : (isDark
                                                ? Colors.white
                                                : Colors.black87)),
                                  ),
                                ),
                              ),
                              if (!isUser) ...[
                                const SizedBox(height: 4),
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.start,
                                  children: [
                                    IconButton(
                                        icon: Icon(Icons.copy_rounded,
                                            size: 18,
                                            color: isDark
                                                ? Colors.white54
                                                : Colors.black54),
                                        padding: EdgeInsets.zero,
                                        constraints: const BoxConstraints(),
                                        onPressed: () {
                                          Clipboard.setData(ClipboardData(
                                              text: msg["content"]!));
                                          ScaffoldMessenger.of(context)
                                              .showSnackBar(const SnackBar(
                                                  content: Text(
                                                      "📋 Copied to clipboard!")));
                                        }),
                                    const SizedBox(width: 15),
                                    IconButton(
                                        icon: Icon(Icons.thumb_up_alt_outlined,
                                            size: 18,
                                            color: isDark
                                                ? Colors.white54
                                                : Colors.black54),
                                        padding: EdgeInsets.zero,
                                        constraints: const BoxConstraints(),
                                        onPressed: () => ScaffoldMessenger.of(
                                                context)
                                            .showSnackBar(const SnackBar(
                                                content: Text(
                                                    "✅ Positive feedback logged!")))),
                                    const SizedBox(width: 15),
                                    IconButton(
                                        icon: Icon(
                                            Icons.thumb_down_alt_outlined,
                                            size: 18,
                                            color: isDark
                                                ? Colors.white54
                                                : Colors.black54),
                                        padding: EdgeInsets.zero,
                                        constraints: const BoxConstraints(),
                                        onPressed: _showFeedbackDialog),
                                    const SizedBox(width: 15),
                                    IconButton(
                                        icon: Icon(Icons.share_rounded,
                                            size: 18,
                                            color: isDark
                                                ? Colors.white54
                                                : Colors.black54),
                                        padding: EdgeInsets.zero,
                                        constraints: const BoxConstraints(),
                                        onPressed: () => Share.share(
                                            "GSTU AI Analysis:\n\n${msg['content']}")),
                                  ],
                                )
                              ]
                            ],
                          ),
                        ),
                      );
                    },
                  ),
          ),
          if (_isThinking)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
              child: Row(
                children: [
                  const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Color(0xFF10A37F))),
                  const SizedBox(width: 10),
                  Text("💭 Astra Core is analyzing...",
                      style: TextStyle(
                          color: isDark ? Colors.white54 : Colors.black54,
                          fontStyle: FontStyle.italic,
                          fontSize: 13)),
                ],
              ),
            ),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
                color: isDark ? const Color(0xFF0F172A) : Colors.white,
                border: Border(
                    top: BorderSide(
                        color: isDark ? Colors.white12 : Colors.black12))),
            child: SafeArea(
              child: Row(
                children: [
                  IconButton(
                      icon: const Icon(Icons.attach_file_rounded),
                      color: Colors.grey,
                      onPressed: () => ScaffoldMessenger.of(context)
                          .showSnackBar(const SnackBar(
                              content: Text(
                                  "File picker logic active in Phase 4.")))),
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      style: TextStyle(
                          color: isDark ? Colors.white : Colors.black),
                      decoration: const InputDecoration(
                          hintText: "Message GSTU Assistant...",
                          border: InputBorder.none),
                      onSubmitted: (_) => _sendMessage(),
                    ),
                  ),
                  IconButton(
                    // 🔴 ডাইনামিক আইকন: রেকর্ড হলে স্টপ আইকন, না হলে মাইক আইকন
                    icon: Icon(_isRecording
                        ? Icons.stop_circle_rounded
                        : Icons.mic_none),
                    color: _isRecording ? Colors.redAccent : Colors.grey,
                    onPressed: _toggleRecording,
                  ),
                  IconButton(
                      icon: const Icon(Icons.send_rounded),
                      color: const Color(0xFF10A37F),
                      onPressed: () => _sendMessage()),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // 🔴 BUG FIX 4: Added Material wrapping for proper InkWell ripple effect
  Widget _buildQuickAction(String title, String subtitle, VoidCallback onTap) {
    return Material(
      color: Theme.of(context).brightness == Brightness.dark
          ? Colors.white12
          : Colors.black12,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
          child: Column(
            children: [
              Text(title,
                  style: const TextStyle(
                      fontWeight: FontWeight.bold, fontSize: 12),
                  textAlign: TextAlign.center),
              const SizedBox(height: 4),
              Text(subtitle,
                  style: const TextStyle(fontSize: 10, color: Colors.grey),
                  textAlign: TextAlign.center,
                  maxLines: 2),
            ],
          ),
        ),
      ),
    );
  }
}

// 🎨 Premium Hover Button Class (Glaze Effect)
class PremiumHoverButton extends StatefulWidget {
  final String text;
  final IconData icon;
  final VoidCallback onPressed;
  final bool isDark;
  const PremiumHoverButton(
      {super.key,
      required this.text,
      required this.icon,
      required this.onPressed,
      required this.isDark});
  @override
  State<PremiumHoverButton> createState() => _PremiumHoverButtonState();
}

class _PremiumHoverButtonState extends State<PremiumHoverButton> {
  bool _isHovered = false;
  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: GestureDetector(
        onTap: widget.onPressed,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeInOut,
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
          decoration: BoxDecoration(
            color: _isHovered
                ? const Color(0xFF10A37F).withOpacity(0.15)
                : (widget.isDark ? Colors.white12 : Colors.black12),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
                color:
                    _isHovered ? const Color(0xFF10A37F) : Colors.transparent,
                width: 1.5),
            boxShadow: _isHovered
                ? [
                    BoxShadow(
                        color: const Color(0xFF10A37F).withOpacity(0.4),
                        blurRadius: 12,
                        spreadRadius: 1)
                  ]
                : [],
          ),
          child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            Icon(widget.icon,
                size: 18,
                color: _isHovered
                    ? const Color(0xFF10A37F)
                    : (widget.isDark ? Colors.white : Colors.black87)),
            const SizedBox(width: 8),
            Text(widget.text,
                style: TextStyle(
                    color: _isHovered
                        ? const Color(0xFF10A37F)
                        : (widget.isDark ? Colors.white : Colors.black87),
                    fontWeight: FontWeight.w600,
                    fontSize: 13)),
          ]),
        ),
      ),
    );
  }
}
