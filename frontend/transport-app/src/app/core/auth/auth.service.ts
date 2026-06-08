import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, throwError } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

interface DecodedToken {
  user_id: string;
  full_name: string;
  email: string;
  role: string;
  exp: number;
  iat: number;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = environment.apiUrl;
  private accessTokenKey = 'access_token';
  private refreshTokenKey = 'refresh_token';
  private userKey = 'user_data';

  private userSubject = new BehaviorSubject<any>(this.getUserFromStorage());
  public user$ = this.userSubject.asObservable();

  constructor(
    private http: HttpClient,
    private router: Router
  ) {
    // Initialize user if token exists
    if (this.isAuthenticated()) {
      this.userSubject.next(this.getUserFromStorage());
    }
  }

  /**
   * Login with email and password
   */
  login(email: string, password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.apiUrl}/auth/login`, {
      email,
      password
    }).pipe(
      map(response => {
        this.storeTokens(response.access_token, response.refresh_token);
        const user = this.decodeToken(response.access_token);
        this.storeUser(user);
        this.userSubject.next(user);
        console.log('AuthService.login: stored tokens and user', user);
        return response;
      }),
      catchError(error => {
        console.error('Login error:', error);
        return throwError(() => error);
      })
    );
  }

  /**
   * Refresh access token
   */
  refreshToken(): Observable<LoginResponse> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      return throwError(() => new Error('No refresh token available'));
    }

    return this.http.post<LoginResponse>(`${this.apiUrl}/auth/refresh`, {
      refresh_token: refreshToken
    }).pipe(
      map(response => {
        this.storeTokens(response.access_token, response.refresh_token);
        const user = this.decodeToken(response.access_token);
        this.storeUser(user);
        this.userSubject.next(user);
        return response;
      }),
      catchError(error => {
        console.error('Refresh token error:', error);
        this.logout();
        return throwError(() => error);
      })
    );
  }

  /**
   * Logout and blacklist tokens
   */
  logout(): Observable<any> {
    const accessToken = this.getAccessToken();
    const refreshToken = this.getRefreshToken();

    const logoutRequest = accessToken && refreshToken
      ? this.http.post(`${this.apiUrl}/auth/logout`, {
          access_token: accessToken,
          refresh_token: refreshToken
        })
      : new Observable(observer => {
          observer.next({});
          observer.complete();
        });

    return logoutRequest.pipe(
      map(() => {
        this.clearTokens();
        this.userSubject.next(null);
        this.router.navigate(['/login']);
        return true;
      }),
      catchError(error => {
        console.error('Logout error:', error);
        this.clearTokens();
        this.userSubject.next(null);
        this.router.navigate(['/login']);
        return throwError(() => error);
      })
    );
  }

  /**
   * Store tokens in localStorage
   */
  private storeTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem(this.accessTokenKey, accessToken);
    localStorage.setItem(this.refreshTokenKey, refreshToken);
  }

  /**
   * Get access token
   */
  getAccessToken(): string | null {
    return localStorage.getItem(this.accessTokenKey);
  }

  /**
   * Get refresh token
   */
  getRefreshToken(): string | null {
    return localStorage.getItem(this.refreshTokenKey);
  }

  /**
   * Clear tokens from localStorage
   */
  private clearTokens(): void {
    localStorage.removeItem(this.accessTokenKey);
    localStorage.removeItem(this.refreshTokenKey);
    localStorage.removeItem(this.userKey);
  }

  /**
   * Store user data in localStorage
   */
  private storeUser(user: DecodedToken): void {
    localStorage.setItem(this.userKey, JSON.stringify(user));
  }

  /**
   * Get user from localStorage
   */
  private getUserFromStorage(): DecodedToken | null {
    const userJson = localStorage.getItem(this.userKey);
    return userJson ? JSON.parse(userJson) : null;
  }

  /**
   * Decode JWT token
   */
  private decodeToken(token: string): DecodedToken {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      return JSON.parse(jsonPayload);
    } catch (error) {
      console.error('Error decoding token:', error);
      throw new Error('Invalid token');
    }
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    const token = this.getAccessToken();
    if (!token) {
      return false;
    }

    try {
      const decoded = this.decodeToken(token);
      const expirationTime = decoded.exp * 1000; // Convert to milliseconds
      return expirationTime > Date.now();
    } catch {
      return false;
    }
  }

  /**
   * Get current user
   */
  getUser(): DecodedToken | null {
    return this.getUserFromStorage();
  }

  /**
   * Get user role
   */
  getUserRole(): string | null {
    const user = this.getUser();
    return user ? user.role : null;
  }

  /**
   * Get user ID
   */
  getUserId(): string | null {
    const user = this.getUser();
    return user ? user.user_id : null;
  }

  /**
   * Check if token is about to expire (within 5 minutes)
   */
  isTokenExpiringSoon(): boolean {
    const token = this.getAccessToken();
    if (!token) {
      return true;
    }

    try {
      const decoded = this.decodeToken(token);
      const expirationTime = decoded.exp * 1000;
      const timeUntilExpiry = expirationTime - Date.now();
      return timeUntilExpiry < 5 * 60 * 1000; // 5 minutes
    } catch {
      return true;
    }
  }
}
