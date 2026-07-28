import { Component, ChangeDetectorRef, ViewChild, ElementRef, AfterViewChecked, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChatService, ChatResponse, SourceData } from './chat.service';
import { SidebarComponent } from './sidebar/sidebar.component';
import { ChatInputComponent } from './chat-input/chat-input.component';
import { marked } from 'marked';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  parsedContent?: string; 
  sources?: SourceData[];
  timestamp: Date;
  isLoading?: boolean;
  error?: string;
}

// 1. New Structure for holding multiple conversations
export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, SidebarComponent, ChatInputComponent],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements AfterViewChecked, OnInit {
  title = 'FinDocGPT Analyst';
  
  // 2. State variables for multi-session support
  sessions: ChatSession[] = [];
  activeSessionId: string | null = null;
  messages: ChatMessage[] = [];
  
  isLoading: boolean = false;
  isDarkMode: boolean = false;
  sessionModel = 'Llama 3.3 70B';
  vectorDb = 'ChromaDB';
  responseTime = '0.00 s';

  @ViewChild('scrollWorkspace') private scrollWorkspace!: ElementRef;

  constructor(
    private chatService: ChatService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadSessions();
    // Intentionally leaving messages empty so the app starts on a fresh blank screen!
  }

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  private scrollToBottom(): void {
    try {
      this.scrollWorkspace.nativeElement.scrollTop = this.scrollWorkspace.nativeElement.scrollHeight;
    } catch(err) { }
  }

  // --- Theme Logic ---
  toggleTheme() {
    this.isDarkMode = !this.isDarkMode;
    if (this.isDarkMode) {
      document.body.classList.add('dark-theme');
    } else {
      document.body.classList.remove('dark-theme');
    }
  }

  // --- Session Management Logic ---
  loadSessions() {
    const saved = localStorage.getItem('findoc_sessions');
    const savedActiveId = localStorage.getItem('findoc_active_session');

    if (saved) {
      this.sessions = JSON.parse(saved);
      
      // Feature: Keep user on the same page after refresh
      if (savedActiveId) {
        const found = this.sessions.find(s => s.id === savedActiveId);
        if (found) {
          this.activeSessionId = found.id;
          this.messages = found.messages;
        }
      }
    }
  }

  saveSessions() {
    localStorage.setItem('findoc_sessions', JSON.stringify(this.sessions));
    
    // Save the active session ID so it survives page refreshes
    if (this.activeSessionId) {
      localStorage.setItem('findoc_active_session', this.activeSessionId);
    } else {
      localStorage.removeItem('findoc_active_session');
    }
  }

  startNewChat() {
    this.activeSessionId = null;
    this.messages = [];
    this.saveSessions();
  }

  loadSpecificSession(sessionId: string) {
    const foundSession = this.sessions.find(s => s.id === sessionId);
    if (foundSession) {
      this.activeSessionId = foundSession.id;
      this.messages = foundSession.messages;
      this.saveSessions();
    }
  }

  // Feature: Delete individual chats
  deleteSpecificSession(sessionId: string) {
    this.sessions = this.sessions.filter(s => s.id !== sessionId);

    // If the user deletes the chat they are currently looking at, clear the screen
    if (this.activeSessionId === sessionId) {
      this.activeSessionId = null;
      this.messages = [];
    }
    
    this.saveSessions();
  }

  clearAllHistory() {
    if (confirm('Are you sure you want to delete all chat history?')) {
      this.sessions = [];
      this.messages = [];
      this.activeSessionId = null;
      localStorage.removeItem('findoc_sessions');
      localStorage.removeItem('findoc_active_session');
    }
  }
  // --- Core Chat Logic ---
  handleNewQuestion(questionText: string) {
    if (!questionText.trim() || this.isLoading) return;
    this.isLoading = true;

    this.messages.push({
      role: 'user',
      content: questionText,
      timestamp: new Date()
    });

    // 3. If this is a brand new chat, create a session for it instantly
    if (!this.activeSessionId) {
      const newSession: ChatSession = {
        id: Date.now().toString(),
        title: questionText.length > 25 ? questionText.substring(0, 25) + '...' : questionText,
        messages: this.messages
      };
      this.sessions.unshift(newSession); // Puts the newest chat at the top of the sidebar list
      this.activeSessionId = newSession.id;
    } else {
      // Update existing session
      const currentSession = this.sessions.find(s => s.id === this.activeSessionId);
      if (currentSession) currentSession.messages = this.messages;
    }
    this.saveSessions();

    const assistantMessage: ChatMessage = {
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true
    };
    this.messages.push(assistantMessage);
    this.cdr.detectChanges(); 

    const startTime = performance.now();

    this.chatService.askQuestion(questionText).subscribe({
      next: async (data: ChatResponse) => {
        assistantMessage.content = data.answer || '';
        assistantMessage.sources = data.sources || [];
        
        if (assistantMessage.content) {
          assistantMessage.parsedContent = await marked.parse(assistantMessage.content);
        }
        
        assistantMessage.isLoading = false;
        const endTime = performance.now();
        this.responseTime = ((endTime - startTime) / 1000).toFixed(2) + ' s';
        this.isLoading = false;
        
        // 4. Save the AI's response to the active session
        const currentSession = this.sessions.find(s => s.id === this.activeSessionId);
        if (currentSession) currentSession.messages = this.messages;
        this.saveSessions();
        
        this.cdr.detectChanges();
      },
      error: (err: any) => {
        assistantMessage.isLoading = false;
        assistantMessage.error = err.error?.detail || err.message || 'Failed to establish connection.';
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  // --- Export Functions ---
  copyText(text: string) {
    navigator.clipboard.writeText(text).then(() => alert('Copied to clipboard!'));
  }
  downloadMarkdown(text: string) {
    const blob = new Blob([text], { type: 'text/markdown' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `FinDocGPT_Analysis.md`;
    a.click();
    window.URL.revokeObjectURL(url);
  }
  downloadPDF() { alert('PDF Export triggered.'); }
  downloadDocx() { alert('DOCX Export triggered.'); }
  viewSourceContext(source: SourceData) {
    alert(`Opening ${source.company} FY${source.fiscal_year}, Page ${source.page_number}`);
  }
}