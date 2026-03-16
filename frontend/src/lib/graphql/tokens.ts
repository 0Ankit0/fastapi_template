import { graphqlRequest } from '@/lib/graphql-client';
import type { PaginatedResponse, TokenTracking } from '@/types';

export async function tokens(params?: {
  skip?: number;
  limit?: number;
}): Promise<PaginatedResponse<TokenTracking>> {
  const data = await graphqlRequest<
    { tokens: PaginatedResponse<TokenTracking> },
    { input?: typeof params }
  >(
    `query Tokens($input: PaginationInput) {
      tokens(input: $input) {
        items {
          id
          user_id
          token_jti
          token_type
          ip_address
          user_agent
          is_active
          revoked_at
          revoke_reason
          expires_at
          created_at
        }
        total
        skip
        limit
      }
    }`,
    { input: params }
  );
  return data.tokens;
}

export async function revokeToken(tokenId: string): Promise<boolean> {
  const data = await graphqlRequest<{ revokeToken: boolean }, { tokenId: string }>(
    `mutation RevokeToken($tokenId: ID!) {
      revokeToken(tokenId: $tokenId)
    }`,
    { tokenId }
  );
  return data.revokeToken;
}

export async function revokeAllTokens(): Promise<boolean> {
  const data = await graphqlRequest<{ revokeAllTokens: boolean }>(
    `mutation RevokeAllTokens {
      revokeAllTokens
    }`
  );
  return data.revokeAllTokens;
}
