import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './sidebar.component.html',
  styleUrls: ['./sidebar.component.css']
})
export class SidebarComponent {
  @Input() sessionModel: string = 'Llama 3.3 70B';
  @Input() vectorDb: string = 'ChromaDB';
  @Input() responseTime: string = '0.00 s';
}