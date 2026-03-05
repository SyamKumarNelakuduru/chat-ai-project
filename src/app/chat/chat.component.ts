import { Component, ChangeDetectionStrategy, ChangeDetectorRef, AfterViewChecked, ViewChild, ElementRef, Pipe, PipeTransform } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { AiService } from '../services/ai.service';

@Pipe({name: 'formatText', standalone: true})
class FormatTextPipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}
  transform(text: string): SafeHtml {
    const formatted = text.replace(/\n/g, '<br>');
    return this.sanitizer.bypassSecurityTrustHtml(formatted);
  }
}

type Sender = 'me' | 'other';

@Component({
  selector: 'app-chat',
  imports: [CommonModule, FormsModule, FormatTextPipe],
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChatComponent implements AfterViewChecked {
  messages: { text: string; sender: Sender }[] = [
    { text: 'Hi 👋 Ask me anything about pharmacy data!', sender: 'other' },
  ];

  newMessage = '';
  isLoading = false;

  @ViewChild('messagesContainer') messagesContainer!: ElementRef;

  constructor(private aiService: AiService, private cdr: ChangeDetectorRef) {}

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  scrollToBottom() {
    if (this.messagesContainer) {
      this.messagesContainer.nativeElement.scrollTop = 
        this.messagesContainer.nativeElement.scrollHeight;
    }
  }

  send() {
    const text = this.newMessage.trim();
    if (!text) return;

    // Add user message to chat
    this.messages.push({ text, sender: 'me' });
    this.newMessage = '';
    this.isLoading = true;
    this.cdr.markForCheck();

    // Call backend service
    this.aiService.askQuestion(text).subscribe({
      next: (response) => {
        console.log('✅ Backend response:', response);
        this.messages.push({ text: response.answer, sender: 'other' });
        this.isLoading = false;
        this.cdr.markForCheck();
      },
      error: (error) => {
        console.error('❌ Backend error:', error);
        this.messages.push({ 
          text: 'Sorry, I couldn\'t reach the backend. Please try again.', 
          sender: 'other' 
        });
        this.isLoading = false;
        this.cdr.markForCheck();
      }
    });
  }
}