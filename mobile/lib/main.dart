import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

// Emulator Android: 10.0.2.2 = localhost laptop. HP asli: --dart-define=API_URL=http://IP_LAPTOP:8000
const baseUrl =
    String.fromEnvironment('API_URL', defaultValue: 'http://10.0.2.2:8000');

class Api {
  String? token;
  String? sessionId;

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  Future<Map<String, dynamic>> _post(String path, [Map<String, dynamic>? body]) async {
    final r = await http.post(Uri.parse('$baseUrl$path'),
        headers: _headers, body: jsonEncode(body ?? {}));
    final data = jsonDecode(utf8.decode(r.bodyBytes));
    if (r.statusCode >= 400) {
      throw Exception(data is Map ? '${data['detail']}' : 'Error ${r.statusCode}');
    }
    return Map<String, dynamic>.from(data as Map);
  }

  Future<void> login(String name) async {
    final r = await _post('/auth/login', {'name': name, 'role': 'pasien'});
    token = r['token'] as String;
  }

  Future<void> consent(bool granted) => _post('/consents', {'granted': granted});

  Future<String> startSession() async {
    final r = await _post('/intake/sessions');
    sessionId = r['session_id'] as String;
    return r['question'] as String;
  }

  Future<Map<String, dynamic>> send(String text) =>
      _post('/intake/sessions/$sessionId/messages', {'text': text});

  Future<void> share() => _post('/intake/sessions/$sessionId/share');
}

final api = Api();

void main() => runApp(const TriaseKuApp());

class TriaseKuApp extends StatelessWidget {
  const TriaseKuApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'TriaseKu',
        theme: ThemeData(colorSchemeSeed: Colors.teal, useMaterial3: true),
        home: const LoginPage(),
      );
}

void showError(BuildContext context, Object e) {
  ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))));
}

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _name = TextEditingController();
  bool _busy = false;

  Future<void> _login() async {
    if (_name.text.trim().isEmpty) return;
    setState(() => _busy = true);
    try {
      await api.login(_name.text.trim());
      if (!mounted) return;
      Navigator.pushReplacement(
          context, MaterialPageRoute(builder: (_) => const ConsentPage()));
    } catch (e) {
      if (mounted) showError(context, e);
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('TriaseKu')),
        body: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            const Text('Cek gejala dan dapatkan arahan tingkat perawatan. '
                'Aplikasi ini bukan pengganti dokter.'),
            const SizedBox(height: 16),
            TextField(
                controller: _name,
                decoration: const InputDecoration(labelText: 'Nama (data sintetis)')),
            const SizedBox(height: 16),
            FilledButton(
                onPressed: _busy ? null : _login, child: const Text('Masuk')),
          ]),
        ),
      );
}

class ConsentPage extends StatelessWidget {
  const ConsentPage({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Persetujuan')),
        body: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text(
                'Jawaban Anda diproses untuk menentukan arahan perawatan dan '
                'dibuatkan ringkasan. Ringkasan baru dilihat dokter jika Anda '
                'membagikannya. Anda dapat mencabut persetujuan kapan saja.'),
            const Spacer(),
            FilledButton(
              onPressed: () async {
                try {
                  await api.consent(true);
                  if (!context.mounted) return;
                  Navigator.pushReplacement(context,
                      MaterialPageRoute(builder: (_) => const ChatPage()));
                } catch (e) {
                  if (context.mounted) showError(context, e);
                }
              },
              child: const Text('Setuju dan lanjut'),
            ),
            TextButton(
                onPressed: () => api.consent(false).then((_) => null),
                child: const Text('Tolak')),
          ]),
        ),
      );
}

class ChatPage extends StatefulWidget {
  const ChatPage({super.key});

  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> {
  final _ctl = TextEditingController();
  final _msgs = <Map<String, String>>[];
  bool _busy = true;

  @override
  void initState() {
    super.initState();
    _guard(() async {
      _msgs.add({'from': 'ai', 'text': await api.startSession()});
    });
  }

  Future<void> _guard(Future<void> Function() fn) async {
    try {
      await fn();
    } catch (e) {
      if (mounted) showError(context, e);
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _send() async {
    final text = _ctl.text.trim();
    if (text.isEmpty || _busy) return;
    _ctl.clear();
    setState(() {
      _msgs.add({'from': 'pasien', 'text': text});
      _busy = true;
    });
    await _guard(() async {
      final r = await api.send(text);
      if (r['done'] == true) {
        if (!mounted) return;
        Navigator.pushReplacement(
            context,
            MaterialPageRoute(
                builder: (_) =>
                    ResultPage(result: Map<String, dynamic>.from(r['result'] as Map))));
        return;
      }
      _msgs.add({'from': 'ai', 'text': '${r['question']}'});
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Cek Gejala')),
        body: Column(children: [
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(12),
              children: [
                for (final m in _msgs)
                  Align(
                    alignment: m['from'] == 'ai'
                        ? Alignment.centerLeft
                        : Alignment.centerRight,
                    child: Card(
                      child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Text(m['text'] ?? '')),
                    ),
                  ),
              ],
            ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: Row(children: [
                Expanded(
                    child: TextField(
                        controller: _ctl,
                        onSubmitted: (_) => _send(),
                        decoration:
                            const InputDecoration(hintText: 'Tulis jawaban...'))),
                IconButton(
                    onPressed: _busy ? null : _send, icon: const Icon(Icons.send)),
              ]),
            ),
          ),
        ]),
      );
}

class ResultPage extends StatelessWidget {
  const ResultPage({super.key, required this.result});

  final Map<String, dynamic> result;

  static const _labels = {
    'DARURAT': 'Darurat: segera ke IGD',
    'KONSULTASI': 'Konsultasi dokter',
    'MANDIRI': 'Perawatan mandiri',
  };
  static const _colors = {
    'DARURAT': Colors.red,
    'KONSULTASI': Colors.amber,
    'MANDIRI': Colors.green,
  };

  @override
  Widget build(BuildContext context) {
    final level = '${result['arahan']}';
    final reasons = List<String>.from(result['alasan'] as List);
    return Scaffold(
      appBar: AppBar(title: const Text('Hasil Arahan')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Card(
          color: _colors[level]?.withValues(alpha: 0.25),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(_labels[level] ?? level,
                  style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              for (final r in reasons) Text('- $r'),
              if (level == 'DARURAT') ...[
                const SizedBox(height: 8),
                const Text('Hubungi 112 atau 119 sekarang.',
                    style: TextStyle(fontWeight: FontWeight.bold)),
              ],
            ]),
          ),
        ),
        const SizedBox(height: 12),
        const Text('Ini bukan diagnosis medis dan tidak menggantikan dokter.'),
        const SizedBox(height: 12),
        FilledButton(
          onPressed: () async {
            try {
              await api.share();
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Ringkasan dibagikan ke dokter')));
              }
            } catch (e) {
              if (context.mounted) showError(context, e);
            }
          },
          child: const Text('Bagikan ringkasan ke dokter'),
        ),
      ]),
    );
  }
}
