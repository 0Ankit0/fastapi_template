import { graphqlRequest } from '@/lib/graphql-client';
import type { PaginatedResponse, User, UserUpdate } from '@/types';

interface UsersQueryData {
  users: PaginatedResponse<User>;
}

interface UserQueryData {
  user: User;
}

interface UpdateProfileMutationData {
  updateProfile: User;
}

interface UpdateUserMutationData {
  updateUser: User;
}

interface DeleteUserMutationData {
  deleteUser: boolean;
}

interface UploadAvatarMutationData {
  uploadAvatar: User;
}

export async function listUsers(params?: {
  skip?: number;
  limit?: number;
  search?: string;
  is_active?: boolean;
}): Promise<PaginatedResponse<User>> {
  const data = await graphqlRequest<UsersQueryData, { input?: typeof params }>(
    `query Users($input: UsersFilterInput) {
      users(input: $input) {
        items {
          id
          username
          email
          first_name
          last_name
          phone
          is_active
          is_verified
          is_superuser
          avatar
          image_url
          bio
          roles
        }
        total
        skip
        limit
      }
    }`,
    { input: params }
  );

  return data.users;
}

export async function getUser(userId: string): Promise<User> {
  const data = await graphqlRequest<UserQueryData, { userId: string }>(
    `query User($userId: ID!) {
      user(userId: $userId) {
        id
        username
        email
        first_name
        last_name
        phone
        is_active
        is_verified
        is_superuser
        avatar
        image_url
        bio
        roles
      }
    }`,
    { userId }
  );

  return data.user;
}

export async function updateProfile(data: UserUpdate): Promise<User> {
  const gql = await graphqlRequest<UpdateProfileMutationData, { input: UserUpdate }>(
    `mutation UpdateProfile($input: UserUpdateInput!) {
      updateProfile(input: $input) {
        id
        username
        email
        first_name
        last_name
        phone
        is_active
        is_verified
        is_superuser
        avatar
        image_url
        bio
        roles
      }
    }`,
    { input: data }
  );

  return gql.updateProfile;
}

export async function updateUser(userId: string, data: UserUpdate): Promise<User> {
  const gql = await graphqlRequest<UpdateUserMutationData, { userId: string; input: UserUpdate }>(
    `mutation UpdateUser($userId: ID!, $input: UserUpdateInput!) {
      updateUser(userId: $userId, input: $input) {
        id
        username
        email
        first_name
        last_name
        phone
        is_active
        is_verified
        is_superuser
        avatar
        image_url
        bio
        roles
      }
    }`,
    { userId, input: data }
  );

  return gql.updateUser;
}

export async function deleteUser(userId: string): Promise<void> {
  await graphqlRequest<DeleteUserMutationData, { userId: string }>(
    `mutation DeleteUser($userId: ID!) {
      deleteUser(userId: $userId)
    }`,
    { userId }
  );
}

export async function uploadAvatar(input: {
  fileName: string;
  contentType: string;
  base64Data: string;
}): Promise<User> {
  const data = await graphqlRequest<UploadAvatarMutationData, { input: typeof input }>(
    `mutation UploadAvatar($input: AvatarUploadInput!) {
      uploadAvatar(input: $input) {
        id
        username
        email
        first_name
        last_name
        phone
        is_active
        is_verified
        is_superuser
        avatar
        image_url
        bio
        roles
      }
    }`,
    { input }
  );

  return data.uploadAvatar;
}
