'use client';

import { useState, useRef } from 'react';
import { useAuthStore } from '@/store/auth-store';
import * as userApi from '@/lib/graphql/users';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Camera, User, Loader2 } from 'lucide-react';

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
const MAX_SIZE_MB = 5;

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const value = String(reader.result ?? '');
      const base64 = value.includes(',') ? value.split(',')[1] : value;
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export function AvatarForm() {
  const { user, setUser } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!ALLOWED_TYPES.includes(file.type)) {
      setError('Please upload a JPEG, PNG, GIF, or WebP image.');
      return;
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      setError(`File must be smaller than ${MAX_SIZE_MB} MB.`);
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const base64Data = await fileToBase64(file);
      const updatedUser = await userApi.uploadAvatar({
        fileName: file.name,
        contentType: file.type,
        base64Data,
      });

      if (user) {
        setUser({ ...user, image_url: updatedUser.image_url });
      }
    } catch {
      setError('Upload failed. Please try again.');
    } finally {
      setIsLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Camera className="h-5 w-5" />
          Profile Picture
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col items-center space-y-4">
        <div className="relative">
          <div className="w-24 h-24 rounded-full bg-gray-200 flex items-center justify-center overflow-hidden">
            {user?.image_url ? (
              <img src={user.image_url} alt="Avatar" className="w-full h-full object-cover" />
            ) : (
              <User className="h-10 w-10 text-gray-400" />
            )}
          </div>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading}
            className="absolute -bottom-1 -right-1 p-2 bg-blue-600 text-white rounded-full hover:bg-blue-700 disabled:opacity-50 transition-colors"
            aria-label="Upload avatar"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Camera className="h-4 w-4" />
            )}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp"
            onChange={handleFileChange}
            className="hidden"
          />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <p className="text-xs text-gray-500 text-center">
          Click the camera icon to upload a photo.
          <br />
          Max {MAX_SIZE_MB} MB · JPEG, PNG, GIF, WebP
        </p>
      </CardContent>
    </Card>
  );
}
