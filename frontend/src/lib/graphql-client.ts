import axios from 'axios';

const graphqlURL = process.env.NEXT_PUBLIC_GRAPHQL_URL || 'http://localhost:8000/api/v1/graphql';

interface GraphQLErrorItem {
  message: string;
}

interface GraphQLResponse<T> {
  data?: T;
  errors?: GraphQLErrorItem[];
}

export class GraphQLRequestError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'GraphQLRequestError';
  }
}

export async function graphqlRequest<
  TData,
  TVariables extends Record<string, unknown> | undefined = undefined,
>(query: string, variables?: TVariables): Promise<TData> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await axios.post<GraphQLResponse<TData>>(
    graphqlURL,
    { query, variables },
    { headers }
  );

  if (response.data.errors?.length) {
    const message = response.data.errors.map((error) => error.message).join(', ');
    throw new GraphQLRequestError(message);
  }

  if (!response.data.data) {
    throw new GraphQLRequestError('GraphQL request returned no data.');
  }

  return response.data.data;
}
